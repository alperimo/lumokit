import base64
import json
import os
import secrets
import struct
import time
from datetime import datetime, timedelta, timezone

import base58
import requests
from base58 import b58decode, b58encode
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.signature import Signature
from sqlalchemy.orm import Session

from models.login_logs import LoginLogs
from models.transactions import Transaction
from models.users import User
from settings.config import CONFIG
from settings.db import get_db
from settings.logger import logger

from .schema import ProUpgradeRequest, UserAuthRequest, UserProStatusRequest

###############################################
##### USER AUTHENTICATION CONTROLLER #####
###############################################


async def verify_signature(public_key: str, signature: str) -> bool:
    try:
        message = f"Sign this message for authenticating with LumoKit: {public_key}"
        message_bytes = message.encode("utf-8")
        signature_bytes = base64.b64decode(signature)

        public_key_obj = Pubkey.from_string(public_key)
        signature_obj = Signature.from_bytes(signature_bytes)
        return signature_obj.verify(public_key_obj, message_bytes)
    except Exception as e:
        logger.error(f"[LUMOKIT] Error verifying signature: {e}")
        return False


async def authenticate_with_signature(user_request: UserAuthRequest, db: Session):
    try:
        # Validate the signature
        is_valid = await verify_signature(
            user_request.public_key, user_request.signature
        )
        if not is_valid:
            logger.error(
                f"[LUMOKIT] Authentication failed: Invalid signature for public key {user_request.public_key}"
            )
            return False

        # Check if the user exists
        user = db.query(User).filter(User.pubkey == user_request.public_key).first()

        # Create a new user if they don't exist
        if not user:
            user = User(pubkey=user_request.public_key)
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(
                f"[LUMOKIT] New user created with public key: {user_request.public_key}"
            )
        else:
            logger.info(
                f"[LUMOKIT] Existing user authenticated with public key: {user_request.public_key}"
            )

        # Create login log
        login_log = LoginLogs(pubkey=user_request.public_key)
        db.add(login_log)
        db.commit()

        logger.info(
            f"[LUMOKIT] Authentication successful for public key: {user_request.public_key}"
        )
        return True
    except Exception as e:
        logger.error(f"[LUMOKIT] Error in authenticate_with_signature: {e}")
        db.rollback()
        return False


###############################################
##### USER PRO STATUS CONTROLLER #####
###############################################


async def check_user_pro_status(user_request, db: Session):
    try:
        # Check if user_request is a dictionary or an object with public_key attribute
        if isinstance(user_request, dict):
            public_key = user_request.get("public_key")
        else:
            public_key = user_request.public_key

        if not public_key:
            logger.error(f"[LUMOKIT] No public key provided for pro status check")
            return {"is_pro": False, "days_remaining": None}

        # Find the user by public key
        user = db.query(User).filter(User.pubkey == public_key).first()

        # If user doesn't exist, return not pro
        if not user:
            logger.info(
                f"[LUMOKIT] User with public key {public_key} not found while verifying pro status."
            )
            return {"is_pro": False, "days_remaining": None}

        # Check if user has pro and if it's still valid
        now = datetime.now()

        if user.premium_end and user.premium_end > now:
            # Calculate days remaining
            days_remaining = (user.premium_end - now).days
            logger.info(
                f"[LUMOKIT] User {public_key} has active pro status with {days_remaining} days remaining"
            )
            return {"is_pro": True, "days_remaining": days_remaining}
        else:
            logger.info(f"[LUMOKIT] User {public_key} does not have pro status")
            return {"is_pro": False, "days_remaining": None}

    except Exception as e:
        logger.error(f"[LUMOKIT] Error in check_user_pro_status: {str(e)}")
        return {"is_pro": False, "days_remaining": None}


###############################################
##### USER PRO UPGRADE CONTROLLER #####
###############################################


def decode_instruction_data(data: str) -> bytes:
    """
    Decode instruction data from base64 or base58 format
    """
    try:
        # Try base64 first
        return base64.b64decode(data)
    except:
        try:
            # Try base58 next
            return b58decode(data)
        except:
            # Return empty bytes if decoding fails
            logger.error(f"[LUMOKIT] Failed to decode instruction data: {data[:30]}")
            return b""


def parse_token_amount(amount_data: bytes, decimals: int = 0) -> int:
    """
    Parse token amount from raw data bytes, with fallback methods
    """
    try:
        # First try to decode as an 8-byte integer (u64)
        if len(amount_data) >= 8:
            return int.from_bytes(amount_data[:8], byteorder="little")
        return 0
    except Exception as e:
        logger.error(f"[LUMOKIT] Error parsing token amount: {str(e)}")
        return 0


async def get_transaction_details(signature: str, max_retries: int = 5) -> tuple:
    """
    Retrieves transaction details from Solana blockchain using RPC
    Returns (success, data/error_message)
    """
    rpc_url = CONFIG.SOLANA_RPC_URL
    headers = {"Content-Type": "application/json"}

    # JSON-RPC payload for getTransaction
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTransaction",
        "params": [
            signature,
            {
                "encoding": "json",
                "maxSupportedTransactionVersion": 0,
                "commitment": "confirmed",
            },
        ],
    }

    retry_count = 0
    retry_delay = 2  # start with 2 seconds delay

    while retry_count < max_retries:
        try:
            logger.info(
                f"[LUMOKIT] Retrieving transaction {signature} details (attempt {retry_count + 1})"
            )

            # Make the JSON-RPC request
            response = requests.post(rpc_url, headers=headers, json=payload, timeout=15)

            # Handle HTTP-level errors
            if response.status_code != 200:
                logger.error(f"[LUMOKIT] Solana RPC error: HTTP {response.status_code}")
                retry_count += 1
                time.sleep(retry_delay)
                retry_delay = min(
                    retry_delay * 1.5, 10
                )  # Exponential backoff with 10s cap
                continue

            # Parse the JSON response
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                logger.error(
                    f"[LUMOKIT] Could not parse JSON response: {response.text[:100]}..."
                )
                retry_count += 1
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 1.5, 10)
                continue

            # Handle JSON-RPC errors
            if "error" in response_data:
                error = response_data["error"]
                # If transaction not found, wait and retry
                if (
                    error.get("code") == -32602
                    or "not found" in error.get("message", "").lower()
                ):
                    logger.warning(
                        f"[LUMOKIT] Transaction {signature} not found yet, retrying..."
                    )
                    retry_count += 1
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * 1.5, 10)
                    continue
                else:
                    error_msg = f"RPC error: {error.get('message', 'Unknown error')}"
                    logger.error(f"[LUMOKIT] {error_msg}")
                    return False, error_msg

            # Extract result data
            result = response_data.get("result")
            if not result:
                logger.warning(
                    f"[LUMOKIT] No result in response for transaction {signature}"
                )
                retry_count += 1
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 1.5, 10)
                continue

            # Check transaction status
            if result.get("meta", {}).get("err") is not None:
                error_msg = f"Transaction failed: {result.get('meta', {}).get('err')}"
                logger.error(f"[LUMOKIT] {error_msg}")
                return False, error_msg

            logger.info(
                f"[LUMOKIT] Successfully retrieved transaction {signature} details"
            )
            return True, result

        except Exception as e:
            error_type = type(e).__name__
            logger.error(
                f"[LUMOKIT] Error retrieving transaction: {error_type} - {str(e)}"
            )
            retry_count += 1
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 1.5, 10)

    logger.error(
        f"[LUMOKIT] Failed to retrieve transaction after {max_retries} attempts"
    )
    return False, f"Failed to retrieve transaction after {max_retries} attempts"


async def verify_spl_token_transfer(
    tx_data: dict, expected_token: str, expected_receiver: str, expected_amount: int
) -> tuple:
    """
    Verifies that a transaction contains a SPL token transfer that matches the requirements
    Returns (success, message)
    """
    try:
        # Get transaction metadata
        meta = tx_data.get("meta", {})
        if not meta:
            return False, "Transaction metadata missing"

        # Get pre and post token balances
        pre_token_balances = meta.get("preTokenBalances", [])
        post_token_balances = meta.get("postTokenBalances", [])

        if not post_token_balances:
            return False, "No token balances found in transaction"

        # Map of account index to pre-balance
        pre_balances = {
            int(balance.get("accountIndex")): int(
                balance.get("uiTokenAmount", {}).get("amount", "0")
            )
            for balance in pre_token_balances
        }

        # Check each post-balance entry
        for balance in post_token_balances:
            # Get mint (token) address
            mint = balance.get("mint")
            if mint != expected_token:
                continue

            # Get owner (recipient) address
            owner = balance.get("owner")
            if owner != expected_receiver:
                continue

            # Get account index and amount
            account_index = int(balance.get("accountIndex"))
            post_amount = int(balance.get("uiTokenAmount", {}).get("amount", "0"))
            pre_amount = pre_balances.get(account_index, 0)

            # Calculate the change in balance
            amount_change = post_amount - pre_amount

            # If the balance increased by at least the expected amount
            if amount_change >= expected_amount:
                logger.info(
                    f"[LUMOKIT] Verified token transfer: {amount_change} tokens to {owner}"
                )
                return True, f"Verified token transfer of {amount_change} tokens"

        # If we get here, no matching transfer was found
        logger.error(f"[LUMOKIT] No matching token transfer found in transaction")
        return False, "No matching token transfer found"

    except Exception as e:
        error_msg = f"Error verifying token transfer: {str(e)}"
        logger.error(f"[LUMOKIT] {error_msg}")
        return False, error_msg


async def validate_transaction_rpc(
    signature: str, expected_token: str, expected_receiver: str, expected_amount: int
) -> tuple:
    """
    Comprehensive validation of a token transfer transaction using Solana RPC
    Returns (success, message)
    """
    # Get transaction details
    success, result = await get_transaction_details(signature)
    if not success:
        return False, result

    # Verify the token transfer
    return await verify_spl_token_transfer(
        result, expected_token, expected_receiver, expected_amount
    )


async def process_pro_upgrade(upgrade_request: ProUpgradeRequest, db: Session):
    """
    Process a pro membership upgrade request by validating the transaction and updating the user's status
    """
    try:
        # Get user from database
        user = db.query(User).filter(User.pubkey == upgrade_request.public_key).first()

        # If user doesn't exist, create a new one
        if not user:
            logger.info(
                f"[LUMOKIT] Creating new user for public key: {upgrade_request.public_key}"
            )
            user = User(pubkey=upgrade_request.public_key)
            db.add(user)
            db.commit()
            db.refresh(user)

        # Check if transaction already processed
        existing_tx = (
            db.query(Transaction)
            .filter(Transaction.tx_hash == upgrade_request.transaction_signature)
            .first()
        )

        if existing_tx and existing_tx.success:
            logger.info(
                f"[LUMOKIT] Transaction {upgrade_request.transaction_signature} already processed"
            )
            return {
                "success": True,
                "message": "Transaction was already processed",
                "premium_end_date": user.premium_end,
            }

        # Validate the transaction using RPC
        logger.info(
            f"[LUMOKIT] Validating transaction {upgrade_request.transaction_signature} for {upgrade_request.public_key}"
        )
        is_valid, validation_message = await validate_transaction_rpc(
            upgrade_request.transaction_signature,
            CONFIG.PRO_MEMBERSHIP_TOKEN,
            CONFIG.PRO_MEMBERSHIP_WALLET,
            CONFIG.PRO_MEMBERSHIP_COST,
        )

        # Create transaction record
        transaction = Transaction(
            pubkey=upgrade_request.public_key,
            tx_hash=upgrade_request.transaction_signature,
            success=is_valid,
        )
        db.add(transaction)

        if not is_valid:
            db.commit()
            logger.error(
                f"[LUMOKIT] Transaction validation failed: {validation_message}"
            )
            return {
                "success": False,
                "message": validation_message,
                "premium_end_date": None,
            }

        # Update user's premium status
        now = datetime.now()
        premium_days = 30  # 30 days for premium membership

        # If user already has premium, add 30 more days to the current end date
        if user.premium_end and user.premium_end > now:
            logger.info(
                f"[LUMOKIT] Extending existing premium for user {upgrade_request.public_key}"
            )
            user.premium_end = user.premium_end + timedelta(days=premium_days)
        else:
            # Otherwise, set premium end to 30 days from now
            logger.info(
                f"[LUMOKIT] Setting new premium for user {upgrade_request.public_key}"
            )
            user.premium_end = now + timedelta(days=premium_days)

        db.commit()
        db.refresh(user)

        logger.info(
            f"[LUMOKIT] Pro upgrade successful for {upgrade_request.public_key}, premium ends at {user.premium_end}"
        )
        return {
            "success": True,
            "message": "Pro membership activated successfully",
            "premium_end_date": user.premium_end,
        }

    except Exception as e:
        logger.error(f"[LUMOKIT] Error in process_pro_upgrade: {str(e)}")
        db.rollback()
        return {
            "success": False,
            "message": f"Error processing upgrade: {str(e)}",
            "premium_end_date": None,
        }


###############################################
##### WALLET GENERATION CONTROLLER #####
###############################################


def derive_key_from_salt(salt: str) -> bytes:
    """
    Derives a Fernet key from the provided salt
    """
    try:
        salt_bytes = salt.encode("utf-8")
        # Use PBKDF2 to derive a secure key from the salt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt_bytes,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(
            kdf.derive(CONFIG.WALLET_ENCRYPTION_SALT.encode("utf-8"))
        )
        return key
    except Exception as e:
        logger.error(f"[LUMOKIT] Error deriving key from salt: {str(e)}")
        # Generate a fallback key if derivation fails
        return Fernet.generate_key()


def encrypt_private_key(private_key: str, salt: str) -> str:
    """
    Encrypts a private key using the provided salt
    """
    try:
        key = derive_key_from_salt(salt)
        f = Fernet(key)
        encrypted_data = f.encrypt(private_key.encode("utf-8"))
        return base64.urlsafe_b64encode(encrypted_data).decode("utf-8")
    except Exception as e:
        logger.error(f"[LUMOKIT] Error encrypting private key: {str(e)}")
        raise ValueError("Failed to encrypt private key")


def decrypt_private_key(encrypted_key: str, salt: str) -> str:
    """
    Decrypts an encrypted private key using the provided salt
    """
    try:
        key = derive_key_from_salt(salt)
        f = Fernet(key)
        encrypted_data = base64.urlsafe_b64decode(encrypted_key.encode("utf-8"))
        decrypted_data = f.decrypt(encrypted_data)
        return decrypted_data.decode("utf-8")
    except Exception as e:
        logger.error(f"[LUMOKIT] Error decrypting private key: {str(e)}")
        raise ValueError("Failed to decrypt private key")


async def generate_new_wallet(wallet_request=None):
    """
    Generates a new Solana wallet with encrypted private key using the config salt
    """
    try:
        # Generate a new Solana keypair
        # First, generate a random seed (32 bytes)
        seed = os.urandom(32)

        # Create a Solana keypair from this seed
        keypair = Keypair.from_seed(seed)

        # Get public key
        public_key = str(keypair.pubkey())

        # Private Key
        full_private_key = seed + bytes(keypair.pubkey())

        # Encode the full private key in base58 format which is what wallets expect
        private_key = base58.b58encode(full_private_key).decode("utf-8")

        # Use the salt from config for encryption
        salt = CONFIG.WALLET_ENCRYPTION_SALT

        # Encrypt the private key with salt
        encrypted_private_key = encrypt_private_key(private_key, salt)

        # Verify decryption works
        try:
            decrypted = decrypt_private_key(encrypted_private_key, salt)
            if decrypted != private_key:
                raise ValueError("Encryption verification failed")
        except Exception as decrypt_error:
            logger.error(
                f"[LUMOKIT] Encryption verification failed: {str(decrypt_error)}"
            )
            raise ValueError("Could not verify encryption/decryption")

        logger.info(f"[LUMOKIT] Generated new wallet with public key: {public_key}")

        # Return response without the salt and network info
        return {
            "public_key": public_key,
            "private_key": private_key,
            "encrypted_private_key": encrypted_private_key,
        }
    except Exception as e:
        logger.error(f"[LUMOKIT] Error generating wallet: {str(e)}")
        raise ValueError(f"Failed to generate wallet: {str(e)}")


###############################################
##### PORTFOLIO CONTROLLER #####
###############################################

# Using BirdEye Mechanism


async def get_wallet_portfolio(public_key: str) -> dict:
    """
    Fetches wallet portfolio data from BirdEye API
    """
    try:
        # API endpoint for BirdEye portfolio
        endpoint = (
            f"https://public-api.birdeye.so/v1/wallet/token_list?wallet={public_key}"
        )
        headers = {
            "X-API-KEY": CONFIG.BIRDEYE_API_KEY,
            "accept": "application/json",
            "x-chain": "solana",
        }

        # Make the API request
        response = requests.get(endpoint, headers=headers, timeout=15)

        # Check response status
        if response.status_code != 200:
            error_msg = f"BirdEye API error: HTTP {response.status_code}"
            logger.error(f"[LUMOKIT] {error_msg}: {response.text}")
            return {"success": False, "error": error_msg}

        # Parse the JSON response
        try:
            data = response.json()

            # Check if API returned success
            if not data.get("success", False):
                error_msg = f"BirdEye API returned unsuccessful response: {data.get('message', 'Unknown error')}"
                logger.error(f"[LUMOKIT] {error_msg}")
                return {"success": False, "error": error_msg}

            return data

        except json.JSONDecodeError:
            error_msg = "Failed to parse BirdEye API response"
            return {"success": False, "error": error_msg}

    except Exception as e:
        error_msg = f"Error fetching portfolio: {str(e)}"
        logger.error(f"[LUMOKIT] {error_msg}")
        return {"success": False, "error": error_msg}


# Using Solana RPC and DexScreener API


async def get_wallet_portfolio_ds(public_key: str) -> dict:
    """
    Fetches wallet portfolio data directly from Solana RPC and DexScreener API for prices
    Does not require BirdEye API
    """
    try:
        # Define multiple fallback RPC endpoints
        rpc_endpoints = [
            CONFIG.SOLANA_RPC_URL,
            "https://api.mainnet-beta.solana.com",  # Public Solana RPC
        ]

        headers = {"Content-Type": "application/json"}
        token_data = None
        sol_data = None

        # Try each RPC endpoint until we get a successful response
        for rpc_url in rpc_endpoints:
            logger.info(f"[LUMOKIT] Fetching wallet details for address: {public_key}")

            # Step 1: Get token accounts by owner
            token_accounts_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTokenAccountsByOwner",
                "params": [
                    public_key,
                    {
                        "programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"  # SPL Token Program ID
                    },
                    {"encoding": "jsonParsed"},
                ],
            }

            try:
                token_response = requests.post(
                    rpc_url, headers=headers, json=token_accounts_payload, timeout=15
                )

                if token_response.status_code == 200:
                    token_data_json = token_response.json()
                    if "error" not in token_data_json:
                        token_data = token_data_json

                        # Step 2: Get SOL balance
                        sol_balance_payload = {
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "getBalance",
                            "params": [public_key],
                        }

                        sol_response = requests.post(
                            rpc_url,
                            headers=headers,
                            json=sol_balance_payload,
                            timeout=15,
                        )

                        if sol_response.status_code == 200:
                            sol_data_json = sol_response.json()
                            if "error" not in sol_data_json:
                                sol_data = sol_data_json
                                break  # We have both token and SOL data, we can exit the loop

                logger.warning(
                    f"[LUMOKIT] RPC endpoint {rpc_url} failed or returned errors. Trying next one."
                )

            except Exception as e:
                logger.warning(f"[LUMOKIT] Error with RPC endpoint {rpc_url}: {str(e)}")
                continue

        # If we couldn't get data from any endpoint, return an error
        if not token_data or not sol_data:
            return {
                "success": False,
                "error": "Could not fetch wallet data from any Solana RPC endpoint. Please try again later.",
                "data": None,
            }

        # Step 3: Get token addresses from accounts
        token_addresses = []
        token_balances = {}

        # Add SOL (wrapped SOL address)
        sol_address = "So11111111111111111111111111111111111111112"
        token_addresses.append(sol_address)

        sol_balance = sol_data["result"]["value"]
        sol_ui_amount = sol_balance / 1_000_000_000  # SOL has 9 decimals

        # Store SOL balance
        token_balances[sol_address] = {
            "decimals": 9,
            "balance": sol_balance,
            "uiAmount": sol_ui_amount,
            "symbol": "SOL",
            "name": "Solana",
        }

        # Process other tokens
        for account in token_data["result"]["value"]:
            try:
                token_info = account["account"]["data"]["parsed"]["info"]
                mint_address = token_info["mint"]
                token_amount = token_info["tokenAmount"]

                # Skip tokens with zero balance
                if int(token_amount["amount"]) == 0:
                    continue

                # Add to token addresses list
                if mint_address not in token_addresses:
                    token_addresses.append(mint_address)

                # Store token balance info
                decimals = token_amount["decimals"]
                balance = int(token_amount["amount"])
                ui_amount = float(token_amount["uiAmount"])

                token_balances[mint_address] = {
                    "decimals": decimals,
                    "balance": balance,
                    "uiAmount": ui_amount,
                    "symbol": "UNKNOWN",  # Will be updated with DexScreener data
                    "name": "Unknown Token",  # Will be updated with DexScreener data
                }
            except Exception as e:
                logger.warning(f"[LUMOKIT] Error processing token account: {str(e)}")
                continue

        # Step 4: Fetch token prices and metadata from DexScreener API
        token_metadata = await fetch_token_metadata_from_dexscreener(token_addresses)

        # Step 5: Prepare the final portfolio items
        token_items = []
        total_usd = 0.0

        # SOL needs separate handling for native SOL vs wrapped SOL address
        sol_metadata = token_metadata.get(sol_address, {})
        if sol_address in token_balances:
            sol_balance_info = token_balances[sol_address]
            sol_price = float(sol_metadata.get("priceUsd", 0))
            sol_value = sol_balance_info["uiAmount"] * sol_price
            total_usd += sol_value

            token_items.append(
                {
                    "address": "So11111111111111111111111111111111111111111",  # Native SOL address
                    "decimals": sol_balance_info["decimals"],
                    "balance": sol_balance_info["balance"],
                    "uiAmount": sol_balance_info["uiAmount"],
                    "chainId": "solana",
                    "name": sol_metadata.get("name", "SOL"),
                    "symbol": sol_metadata.get("symbol", "SOL"),
                    "icon": sol_metadata.get("logoURI"),
                    "logoURI": sol_metadata.get("logoURI"),
                    "priceUsd": sol_price,
                    "valueUsd": sol_value,
                }
            )

        # Process all other tokens
        for mint_address, balance_info in token_balances.items():
            # Skip SOL as it's already processed
            if mint_address == sol_address:
                continue

            metadata = token_metadata.get(mint_address, {})
            price_usd = float(metadata.get("priceUsd", 0))

            # Use metadata values when available, fallback to defaults
            symbol = metadata.get("symbol", balance_info["symbol"])
            name = metadata.get("name", balance_info["name"])
            logo_uri = metadata.get("logoURI")

            # Calculate USD value
            value_usd = balance_info["uiAmount"] * price_usd
            total_usd += value_usd

            token_items.append(
                {
                    "address": mint_address,
                    "decimals": balance_info["decimals"],
                    "balance": balance_info["balance"],
                    "uiAmount": balance_info["uiAmount"],
                    "chainId": "solana",
                    "name": name,
                    "symbol": symbol,
                    "icon": logo_uri,
                    "logoURI": logo_uri,
                    "priceUsd": price_usd,
                    "valueUsd": value_usd,
                }
            )

        # Construct the final response
        portfolio_data = {
            "wallet": public_key,
            "totalUsd": total_usd,
            "items": token_items,
        }

        return {"success": True, "data": portfolio_data, "error": None}

    except Exception as e:
        error_msg = f"Error fetching portfolio: {str(e)}"
        logger.error(f"[LUMOKIT] {error_msg}")
        return {"success": False, "error": error_msg, "data": None}


async def fetch_token_metadata_from_dexscreener(token_addresses):
    """
    Fetches token price and metadata from DexScreener API
    DexScreener allows querying multiple tokens (up to 30) in a single request
    """
    try:
        results = {}

        # DexScreener allows up to 30 tokens per request, so batch them
        batch_size = 30

        # Process tokens in batches
        for i in range(0, len(token_addresses), batch_size):
            batch = token_addresses[i : i + batch_size]

            # Format the addresses for the API call
            addresses_param = ",".join(batch)

            # Make request to DexScreener API with retries
            max_retries = 3
            retry_delay = 1  # Start with 1 second delay

            for retry in range(max_retries):
                try:
                    dex_url = f"https://api.dexscreener.com/tokens/v1/solana/{addresses_param}"
                    response = requests.get(dex_url, timeout=15)

                    if response.status_code == 200:
                        # Parse response
                        dex_data = response.json()

                        # First collect all pairs for each token to find the best price data
                        token_pairs = {}

                        # Group pairs by token address
                        for pair in dex_data:
                            # Handle base token
                            base_address = pair.get("baseToken", {}).get("address")
                            if base_address:
                                # Normalize address (remove trailing '2' if needed)
                                normalized_address = (
                                    base_address[:-1]
                                    if base_address.endswith("2")
                                    else base_address
                                )

                                # Add to token_pairs dictionary
                                if normalized_address not in token_pairs:
                                    token_pairs[normalized_address] = []
                                token_pairs[normalized_address].append(
                                    {"role": "base", "pair": pair}
                                )

                            # Handle quote token
                            quote_address = pair.get("quoteToken", {}).get("address")
                            if quote_address:
                                # Normalize address
                                normalized_address = (
                                    quote_address[:-1]
                                    if quote_address.endswith("2")
                                    else quote_address
                                )

                                # Add to token_pairs dictionary
                                if normalized_address not in token_pairs:
                                    token_pairs[normalized_address] = []
                                token_pairs[normalized_address].append(
                                    {"role": "quote", "pair": pair}
                                )

                        # Now process each token to extract the best metadata and price
                        for address in batch:
                            normalized_address = (
                                address[:-1] if address.endswith("2") else address
                            )

                            if normalized_address in token_pairs:
                                # Get all pairs for this token
                                pairs_info = token_pairs[normalized_address]

                                # Sort pairs by liquidity to find the most liquid pair
                                pairs_info.sort(
                                    key=lambda p: float(
                                        p["pair"].get("liquidity", {}).get("usd", 0)
                                        or 0
                                    ),
                                    reverse=True,
                                )

                                # Use the most liquid pair as the price source
                                if pairs_info:
                                    best_pair_info = pairs_info[0]
                                    pair = best_pair_info["pair"]
                                    role = best_pair_info["role"]

                                    # Extract token data based on role (base or quote)
                                    if role == "base":
                                        token_data = pair.get("baseToken", {})
                                        price_usd = pair.get("priceUsd", "0")
                                    else:  # role == "quote"
                                        token_data = pair.get("quoteToken", {})
                                        # For quote tokens, if we have priceUsd in the pair, it's for the base token
                                        # We can derive the quote token price if we have priceNative
                                        price_native = pair.get("priceNative")
                                        try:
                                            if price_native and float(price_native) > 0:
                                                # Get the USD price of the base token
                                                base_price_usd = pair.get("priceUsd")
                                                if base_price_usd:
                                                    # Calculate quote token price: base_price_usd / price_native
                                                    price_usd = str(
                                                        float(base_price_usd)
                                                        / float(price_native)
                                                    )
                                                else:
                                                    price_usd = "0"
                                            else:
                                                price_usd = "0"
                                        except (ValueError, ZeroDivisionError):
                                            price_usd = "0"

                                    # Extract image from pair info
                                    image_url = None
                                    if "info" in pair and "imageUrl" in pair["info"]:
                                        image_url = pair["info"]["imageUrl"]

                                    # Create result for this token
                                    results[address] = {
                                        "symbol": token_data.get("symbol", "UNKNOWN"),
                                        "name": token_data.get("name", "Unknown Token"),
                                        "priceUsd": price_usd,
                                        "logoURI": image_url,
                                    }

                        # We got a successful response, break out of retry loop
                        break
                    else:
                        logger.warning(
                            f"[LUMOKIT] DexScreener API error: HTTP {response.status_code}, retry {retry + 1}/{max_retries}"
                        )
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                except Exception as e:
                    logger.warning(
                        f"[LUMOKIT] Error fetching from DexScreener, retry {retry + 1}/{max_retries}: {str(e)}"
                    )
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff

        # For any tokens that weren't found, set default metadata
        for address in token_addresses:
            if address not in results:
                results[address] = {
                    "symbol": "UNKNOWN",
                    "name": "Unknown Token",
                    "priceUsd": "0",
                    "logoURI": None,
                }

        return results

    except Exception as e:
        logger.error(
            f"[LUMOKIT] Error fetching token metadata from DexScreener: {str(e)}"
        )
        return {}

import base64
import json
from typing import ClassVar, List, Type

import aiohttp
import base58
import requests
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from solana.rpc.api import Client
from solders.hash import Hash
from solders.keypair import Keypair
from solders.message import MessageV0
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import get_associated_token_address

from helper.decrypt_private import WalletDecryptor
from settings.config import CONFIG
from settings.logger import logger

#################################################
#### JUPITER TOKEN PRICE TOOL ####
#################################################


class JupiterTokenPriceInput(BaseModel):
    """Input for the Jupiter token price tool."""

    token_addresses: str = Field(
        ..., description="Comma-separated token addresses to check prices on Jupiter"
    )


class JupiterTokenPriceTool(BaseTool):
    """Tool for getting the current price of multiple tokens in USD using Jupiter."""

    name: ClassVar[str] = "jupiter_token_price_tool"
    description: ClassVar[str] = (
        "Get the current price of one or more Solana tokens in USD from Jupiter. Provide comma-separated token addresses."
    )
    args_schema: ClassVar[Type[BaseModel]] = JupiterTokenPriceInput

    async def _arun(self, token_addresses: str) -> str:
        """Execute the Jupiter token price lookup asynchronously."""
        try:
            logger.info(f"[LUMOKIT] Jupiter token price lookup for: {token_addresses}")

            # Clean up the token addresses (remove spaces)
            token_addresses = token_addresses.strip()

            # Construct the API URL for Jupiter
            api_url = f"https://lite-api.jup.ag/price/v2?ids={token_addresses}"

            # Make the API request
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url) as response:
                    if response.status != 200:
                        logger.error(
                            f"[LUMOKIT] Error fetching Jupiter price data: {response.status} - {await response.text()}"
                        )
                        return f"Failed to get token prices. The API returned a {response.status} error."

                    price_data = await response.json()

            if not price_data or "data" not in price_data:
                logger.error(
                    f"[LUMOKIT] Invalid Jupiter price data format: {price_data}"
                )
                return "Failed to get token prices. The API returned an invalid response format."

            # Format the results in a readable way
            result_lines = ["## Token Prices from Jupiter"]

            for token_address, token_info in price_data["data"].items():
                price = token_info.get("price")
                if price:
                    try:
                        price_float = float(price)
                        formatted_price = "{:.6f}".format(price_float)
                        result_lines.append(f"- **Token**: {token_address}")
                        result_lines.append(f"  **Price**: ${formatted_price} USD")
                    except ValueError:
                        result_lines.append(f"- **Token**: {token_address}")
                        result_lines.append(
                            f"  **Price**: Error - Could not parse price value"
                        )
                else:
                    result_lines.append(f"- **Token**: {token_address}")
                    result_lines.append(f"  **Price**: Not available")

            return "\n".join(result_lines)

        except Exception as e:
            logger.error(f"[LUMOKIT] Error in Jupiter token price tool: {str(e)}")
            return f"Failed to get token prices. An error occurred: {str(e)}"

    def _run(self, token_addresses: str) -> str:
        """Synchronous version returns a message instead of raising an error."""
        return "This tool only supports asynchronous execution. Please use the async version instead."


#################################################
#### JUPITER TOKEN INFORMATION TOOL ####
#################################################


class JupiterTokenInformationInput(BaseModel):
    """Input for the Jupiter token information tool."""

    token_address: str = Field(
        ..., description="The token address to get information about"
    )


class JupiterTokenInformationTool(BaseTool):
    """Tool for getting detailed information about a token using Jupiter."""

    name: ClassVar[str] = "jupiter_token_information_tool"
    description: ClassVar[str] = (
        "Get detailed token information and metadata for a specific Solana token from Jupiter. Provides details like name, symbol, decimals, and other token attributes."
    )
    args_schema: ClassVar[Type[BaseModel]] = JupiterTokenInformationInput

    async def _arun(self, token_address: str) -> str:
        """Execute the Jupiter token information lookup asynchronously."""
        try:
            logger.info(
                f"[LUMOKIT] Jupiter token information lookup for: {token_address}"
            )

            # Clean up the token address (remove spaces)
            token_address = token_address.strip()

            # Construct the API URL for Jupiter token information
            api_url = f"https://lite-api.jup.ag/tokens/v1/token/{token_address}"

            # Make the API request
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url) as response:
                    if response.status != 200:
                        logger.error(
                            f"[LUMOKIT] Error fetching Jupiter token information: {response.status} - {await response.text()}"
                        )
                        return f"Failed to get token information. The API returned a {response.status} error."

                    token_data = await response.json()

            # Format the results in a readable way
            if not token_data:
                return f"No information found for token address: {token_address}"

            # Extract relevant information
            name = token_data.get("name", "Unknown")
            symbol = token_data.get("symbol", "Unknown")
            decimals = token_data.get("decimals", "Unknown")
            logo_uri = token_data.get("logoURI", "None")
            tags = token_data.get("tags", [])
            daily_volume = token_data.get("daily_volume", "Unknown")
            created_at = token_data.get("created_at", "Unknown")
            minted_at = token_data.get("minted_at", "Unknown")

            # Format tags if they exist
            tags_str = ", ".join(tags) if tags else "None"

            # Build a markdown response
            result = [
                f"## Token Information for {name} ({symbol})",
                f"**Address**: {token_address}",
                f"**Name**: {name}",
                f"**Symbol**: {symbol}",
                f"**Decimals**: {decimals}",
                f"**Daily Volume**: {daily_volume if daily_volume != 'Unknown' else 'Not available'}",
                f"**Created**: {created_at if created_at != 'Unknown' else 'Not available'}",
                f"**Minted**: {minted_at if minted_at != 'Unknown' else 'Not available'}",
                f"**Tags**: {tags_str}",
            ]

            # Only include logo if it exists
            if logo_uri != "None":
                result.append(f"**Logo**: {logo_uri}")

            # Add additional metadata if present
            extensions = token_data.get("extensions", {})
            if extensions:
                result.append("\n### Additional Metadata")
                for key, value in extensions.items():
                    result.append(f"**{key}**: {value}")

            return "\n".join(result)

        except Exception as e:
            logger.error(f"[LUMOKIT] Error in Jupiter token information tool: {str(e)}")
            return f"Failed to get token information. An error occurred: {str(e)}"

    def _run(self, token_address: str) -> str:
        """Synchronous version returns a message instead of raising an error."""
        return "This tool only supports asynchronous execution. Please use the async version instead."


#################################################
#### JUPITER SWAP TOOL ####
#################################################


class JupiterSwapInput(BaseModel):
    """Input for the Jupiter swap tool."""

    agent_public: str = Field(
        ..., description="Public key of the agent wallet to swap from"
    )
    agent_private: str = Field(
        ..., description="Encrypted private key of the agent wallet"
    )
    input_mint: str = Field(
        ..., description="Token address of the input token (e.g., SOL mint address)"
    )
    output_mint: str = Field(
        ..., description="Token address of the output token (e.g., USDC mint address)"
    )
    amount: float = Field(..., description="Amount of input tokens to swap")
    slippage: float = Field(
        10.0, description="Slippage tolerance in percentage (default: 10%)"
    )


class JupiterSwapTool(BaseTool):
    """Tool for swapping tokens using Jupiter."""

    name: ClassVar[str] = "jupiter_swap_tool"
    description: ClassVar[str] = (
        "Swap tokens on Solana using Jupiter. Provide the input token, output token, amount, and slippage (default 10%)."
    )
    args_schema: ClassVar[Type[BaseModel]] = JupiterSwapInput

    async def _arun(
        self,
        agent_public: str,
        agent_private: str,
        input_mint: str,
        output_mint: str,
        amount: float,
        slippage: float = 10.0,
    ) -> str:
        """Execute the Jupiter token swap asynchronously."""
        try:
            logger.info(
                f"[LUMOKIT] Jupiter swap initiated: {input_mint} -> {output_mint}"
            )

            # Basic validation
            if amount <= 0:
                return "Amount must be greater than 0."

            # Clean up addresses
            agent_public = agent_public.strip()
            input_mint = input_mint.strip()
            output_mint = output_mint.strip()

            # Fix SOL addresses
            correct_sol_address = "So11111111111111111111111111111111111111112"

            # Check if this is a SOL address and fix it
            if input_mint.lower() == "sol" or input_mint.startswith(
                "So11111111111111111111111111111111111111111"
            ):
                input_mint = correct_sol_address
                logger.info(
                    f"[LUMOKIT] Corrected input_mint to the proper SOL address: {input_mint}"
                )

            if output_mint.lower() == "sol" or output_mint.startswith(
                "So11111111111111111111111111111111111111111"
            ):
                output_mint = correct_sol_address
                logger.info(
                    f"[LUMOKIT] Corrected output_mint to the proper SOL address: {output_mint}"
                )

            # Convert slippage from percentage to basis points
            slippage_bps = int(slippage * 100)

            # Decrypt private key and create keypair
            try:
                decrypted_key = await WalletDecryptor.decrypt_wallet(agent_private)
                private_key_bytes = base58.b58decode(decrypted_key)

                if len(private_key_bytes) == 64:
                    keypair = Keypair.from_bytes(private_key_bytes)
                else:
                    keypair = Keypair.from_seed(private_key_bytes)

                # Simple check that the key is correct
                if str(keypair.pubkey()) != agent_public:
                    return "Public key mismatch. The private key doesn't match the provided public key."
            except Exception as e:
                logger.error(f"[LUMOKIT] Error with private key: {str(e)}")
                return f"Error with private key: {str(e)}"

            # Connect to Solana
            solana_client = Client(CONFIG.SOLANA_RPC_URL)

            # Get token decimals for the input token
            try:
                # If input is SOL, use 9 decimals
                if input_mint.lower() == correct_sol_address.lower():
                    decimals = 9
                else:
                    token_info = solana_client.get_token_supply(
                        Pubkey.from_string(input_mint)
                    )
                    if hasattr(token_info, "value"):
                        decimals = token_info.value.decimals
                    else:
                        decimals = token_info["result"]["value"]["decimals"]

                # Calculate token amount with decimals
                token_amount = int(amount * (10**decimals))
            except Exception as e:
                logger.error(f"[LUMOKIT] Error getting token decimals: {str(e)}")
                return f"Error getting token information: {str(e)}"

            # SIMPLIFIED BALANCE CHECK
            try:
                sender_pubkey = Pubkey.from_string(agent_public)
                token_mint_pubkey = Pubkey.from_string(input_mint)

                # For SOL input
                if input_mint.lower() == correct_sol_address.lower():
                    # CRITICAL FIX: When buying with SOL, we need to first get the quote to know how much SOL is needed
                    # For now just check if there's some SOL in the wallet for fees
                    balance_response = solana_client.get_balance(sender_pubkey)
                    if hasattr(balance_response, "value"):
                        balance_lamports = balance_response.value
                    else:
                        balance_lamports = balance_response["result"]["value"]

                    balance = (
                        balance_lamports / 1_000_000_000
                    )  # Convert lamports to SOL

                    # Only check if we have at least some SOL for transaction fees
                    if balance < 0.005:  # Minimum SOL for transaction fees
                        return f"Insufficient SOL for transaction fees. You need at least 0.005 SOL."

                    logger.info(
                        f"[LUMOKIT] Basic SOL balance check passed: {balance:.5f} SOL available"
                    )

                else:
                    # For SPL tokens
                    source_token_account = get_associated_token_address(
                        sender_pubkey, token_mint_pubkey
                    )

                    # Check if token account exists
                    account_info = solana_client.get_account_info(source_token_account)
                    account_exists = False
                    if hasattr(account_info, "value"):
                        account_exists = account_info.value is not None
                    else:
                        account_exists = account_info["result"]["value"] is not None

                    if not account_exists:
                        return f"You don't have a token account for {input_mint}. Please make sure you own this token before swapping."

                    # Basic token balance check
                    balance_info = solana_client.get_token_account_balance(
                        source_token_account
                    )
                    token_balance = 0
                    if hasattr(balance_info, "value"):
                        token_balance = int(balance_info.value.amount)
                    else:
                        token_balance = int(balance_info["result"]["value"]["amount"])

                    if token_balance < token_amount:
                        human_readable_balance = token_balance / (10**decimals)
                        return f"Insufficient token balance. Wallet has {human_readable_balance} tokens, but you need {amount}."

                    # Check if some SOL is available for fees
                    sol_balance_response = solana_client.get_balance(sender_pubkey)
                    if hasattr(sol_balance_response, "value"):
                        sol_balance_lamports = sol_balance_response.value
                    else:
                        sol_balance_lamports = sol_balance_response["result"]["value"]

                    sol_balance = sol_balance_lamports / 1_000_000_000

                    if sol_balance < 0.001:
                        return f"Insufficient SOL for transaction fees. You need at least 0.001 SOL to cover fees."

                logger.info(
                    f"[LUMOKIT] Balance check passed for input token {input_mint}"
                )

            except Exception as e:
                logger.error(f"[LUMOKIT] Error checking token balance: {str(e)}")
                return f"Error checking token balance: {str(e)}"

            # Step 1: Get a quote from Jupiter
            quote_url = f"https://quote-api.jup.ag/v6/quote?inputMint={input_mint}&outputMint={output_mint}&amount={token_amount}&slippageBps={slippage_bps}"

            logger.info(f"[LUMOKIT] Getting Jupiter quote: {quote_url}")

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(quote_url) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            logger.error(
                                f"[LUMOKIT] Jupiter quote API error: {response.status} - {error_text}"
                            )
                            return f"Failed to get swap quote. The API returned a {response.status} error: {error_text}"

                        quote_data = await response.json()

                if not quote_data:
                    return "Failed to get swap quote. No data returned from Jupiter."

                # ADDITIONAL CHECK: For SOL input, verify we have enough SOL after getting the quote
                if input_mint.lower() == correct_sol_address.lower():
                    # Extract the actual SOL amount needed from the quote
                    input_amount = quote_data.get("inputAmount")
                    if input_amount:
                        sol_needed = (
                            int(input_amount) / 1_000_000_000
                        )  # Convert lamports to SOL

                        # Now check if we have enough SOL
                        if balance < sol_needed + 0.005:  # Add buffer for fees
                            return f"Insufficient SOL balance. Wallet has {balance:.5f} SOL, but you need approximately {sol_needed:.5f} SOL plus fees for this swap."

                        logger.info(
                            f"[LUMOKIT] Full SOL balance check passed: {balance:.5f} SOL available, ~{sol_needed:.5f} SOL needed"
                        )

            except Exception as e:
                logger.error(f"[LUMOKIT] Error fetching Jupiter quote: {str(e)}")
                return f"Failed to get swap quote: {str(e)}"

            # Step 2: Get the serialized transaction for the swap
            try:
                swap_url = "https://quote-api.jup.ag/v6/swap"
                swap_payload = {
                    "quoteResponse": quote_data,
                    "userPublicKey": agent_public,
                    "wrapAndUnwrapSol": True,
                }

                async with aiohttp.ClientSession() as session:
                    async with session.post(swap_url, json=swap_payload) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            logger.error(
                                f"[LUMOKIT] Jupiter swap API error: {response.status} - {error_text}"
                            )
                            return f"Failed to prepare swap transaction. The API returned a {response.status} error: {error_text}"

                        swap_data = await response.json()

                if not swap_data or "swapTransaction" not in swap_data:
                    return "Failed to prepare swap transaction. No transaction data returned from Jupiter."

                # Extract the base64 encoded transaction
                swap_transaction_base64 = swap_data["swapTransaction"]
            except Exception as e:
                logger.error(
                    f"[LUMOKIT] Error preparing Jupiter swap transaction: {str(e)}"
                )
                return f"Failed to prepare swap transaction: {str(e)}"

            # Step 3: Deserialize the transaction
            try:
                # Use the correct approach to deserialize the transaction
                swap_transaction_bytes = base64.b64decode(swap_transaction_base64)

                # Using from_bytes to create the transaction object
                transaction = VersionedTransaction.from_bytes(swap_transaction_bytes)

                logger.info(f"[LUMOKIT] Successfully deserialized transaction")
            except Exception as e:
                logger.error(f"[LUMOKIT] Error deserializing transaction: {str(e)}")
                return f"Failed to process swap transaction: {str(e)}"

            try:
                # Get the message from the transaction
                message = transaction.message

                # Create a new signed transaction
                # Note: This creates a new VersionedTransaction with the message and our keypair
                signed_tx = VersionedTransaction(message, [keypair])

                logger.info(f"[LUMOKIT] Successfully signed transaction")
            except Exception as e:
                logger.error(f"[LUMOKIT] Error signing transaction: {str(e)}")
                return f"Failed to sign swap transaction: {str(e)}"

            # Step 5: Get latest blockhash and execute the transaction
            try:
                # Get the latest blockhash directly via RPC
                headers = {"Content-Type": "application/json"}
                data = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getLatestBlockhash",
                    "params": [],
                }

                response = requests.post(
                    CONFIG.SOLANA_RPC_URL, headers=headers, data=json.dumps(data)
                )
                result = response.json()
                blockhash_str = result["result"]["value"]["blockhash"]
                blockhash = Hash.from_string(blockhash_str)

                # Serialize the signed transaction and send it
                serialized_tx = bytes(signed_tx)  # Using the signed_tx variable here

                send_response = solana_client.send_raw_transaction(serialized_tx)

                # Get the transaction signature
                if hasattr(send_response, "value"):
                    signature = str(send_response.value)
                else:
                    signature = send_response["result"]

                # Wait for transaction confirmation

                explorer_url = f"https://solscan.io/tx/{signature}"
                return f"Jupiter transaction was successfully sent, transaction hash is {signature}, you can view the txn details at {explorer_url}"

            except Exception as e:
                logger.error(f"[LUMOKIT] Error executing swap: {str(e)}")
                return f"Failed to execute swap: {str(e)}"

        except Exception as e:
            logger.error(f"[LUMOKIT] Error in Jupiter swap tool: {str(e)}")
            return f"Failed to perform swap: {str(e)}"

    def _run(
        self,
        agent_public: str,
        agent_private: str,
        input_mint: str,
        output_mint: str,
        amount: float,
        slippage: float = 10.0,
    ) -> str:
        """Synchronous version returns a message instead of raising an error."""
        return "This tool only supports asynchronous execution. Please use the async version instead."

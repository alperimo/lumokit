import json
import struct
from typing import ClassVar, Type

import base58
import requests
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from solana.rpc.api import Client
from solders.hash import Hash
from solders.instruction import AccountMeta
from solders.instruction import Instruction as TransactionInstruction
from solders.keypair import Keypair
from solders.message import MessageV0
from solders.pubkey import Pubkey
from solders.system_program import TransferParams, transfer
from solders.transaction import VersionedTransaction
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import (create_associated_token_account,
                                    get_associated_token_address)

from helper.decrypt_private import WalletDecryptor
from settings.config import CONFIG
from settings.logger import logger

#################################################
#### SOLANA SEND SOL TOOL ####
#################################################


class SolanaSendSolInput(BaseModel):
    """Input for the Solana Send SOL tool."""

    agent_public: str = Field(
        ..., description="Public key of the agent wallet to send from"
    )
    agent_private: str = Field(
        ..., description="Encrypted private key of the agent wallet"
    )
    recipient_address: str = Field(
        ..., description="Solana wallet address to send SOL to"
    )
    amount_sol: float = Field(..., description="Amount of SOL to send (e.g., 0.1)")


class SolanaSendSolTool(BaseTool):
    """Tool for sending SOL from one wallet to another."""

    name: ClassVar[str] = "solana_send_sol_tool"
    description: ClassVar[str] = (
        "Send SOL from agent wallet to a specified Solana address."
    )
    args_schema: ClassVar[Type[BaseModel]] = SolanaSendSolInput

    async def _arun(
        self,
        agent_public: str,
        agent_private: str,
        recipient_address: str,
        amount_sol: float,
    ) -> str:
        """Execute the Solana SOL transfer asynchronously."""
        try:
            logger.info(
                f"[LUMOKIT] Solana Send SOL initiated: {agent_public} -> {recipient_address}"
            )

            # Basic validation
            if amount_sol <= 0:
                return "Amount must be greater than 0 SOL."

            # Clean up addresses
            agent_public = agent_public.strip()
            recipient_address = recipient_address.strip()

            # Parse addresses
            sender_pubkey = Pubkey.from_string(agent_public)
            recipient_pubkey = Pubkey.from_string(recipient_address)

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

            # Check the balance
            balance_response = solana_client.get_balance(sender_pubkey)
            if hasattr(balance_response, "value"):
                balance_lamports = balance_response.value
            else:
                balance_lamports = balance_response["result"]["value"]

            balance_sol = balance_lamports / 1_000_000_000
            amount_lamports = int(amount_sol * 1_000_000_000)

            if balance_sol < amount_sol + 0.001:
                return f"Insufficient balance. Wallet has {balance_sol:.5f} SOL."

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

            # Create the transfer instruction
            ix = transfer(
                TransferParams(
                    from_pubkey=sender_pubkey,
                    to_pubkey=recipient_pubkey,
                    lamports=amount_lamports,
                )
            )

            # Create versioned transaction
            msg = MessageV0.try_compile(
                payer=sender_pubkey,
                instructions=[ix],
                address_lookup_table_accounts=[],
                recent_blockhash=blockhash,
            )

            tx = VersionedTransaction(msg, [keypair])

            serialized_tx = bytes(tx)

            # Send transaction
            # The send_raw_transaction method expects the raw transaction bytes
            send_response = solana_client.send_raw_transaction(serialized_tx)

            # Get the transaction signature
            if hasattr(send_response, "value"):
                signature = str(send_response.value)
            else:
                signature = send_response["result"]

            explorer_url = f"https://solscan.io/tx/{signature}"
            return f"Transaction was successfully sent, transaction hash is {signature}, you can view the txn details at {explorer_url}"

        except Exception as e:
            logger.error(f"[LUMOKIT] Error sending SOL: {str(e)}")
            return f"Failed to send SOL: {str(e)}"

    def _run(
        self,
        agent_public: str,
        agent_private: str,
        recipient_address: str,
        amount_sol: float,
    ) -> str:
        """Synchronous version returns a message instead of raising an error."""
        return "This tool only supports asynchronous execution. Please use the async version instead."


#################################################
#### SOLANA SEND SPL TOKENS TOOL ####
#################################################


class SolanaSendSplTokensInput(BaseModel):
    """Input for the Solana Send SPL Tokens tool."""

    agent_public: str = Field(
        ..., description="Public key of the agent wallet to send from"
    )
    agent_private: str = Field(
        ..., description="Encrypted private key of the agent wallet"
    )
    recipient_address: str = Field(
        ..., description="Solana wallet address to send tokens to"
    )
    token_address: str = Field(
        ..., description="SPL token address (mint address) of the token to send"
    )
    amount: float = Field(..., description="Amount of tokens to send")


class SolanaSendSplTokensTool(BaseTool):
    """Tool for sending SPL tokens from one wallet to another."""

    name: ClassVar[str] = "solana_send_spl_tokens_tool"
    description: ClassVar[str] = (
        "Send SPL tokens from agent wallet to a specified Solana address."
    )
    args_schema: ClassVar[Type[BaseModel]] = SolanaSendSplTokensInput

    async def _arun(
        self,
        agent_public: str,
        agent_private: str,
        recipient_address: str,
        token_address: str,
        amount: float,
    ) -> str:
        """Execute the Solana SPL token transfer asynchronously."""
        try:
            logger.info(
                f"[LUMOKIT] Solana Send SPL Tokens initiated: {agent_public} -> {recipient_address}"
            )

            # Basic validation
            if amount <= 0:
                return "Amount must be greater than 0."

            # Clean up addresses
            agent_public = agent_public.strip()
            recipient_address = recipient_address.strip()
            token_address = token_address.strip()

            # Parse addresses
            sender_pubkey = Pubkey.from_string(agent_public)
            recipient_pubkey = Pubkey.from_string(recipient_address)
            token_mint_pubkey = Pubkey.from_string(token_address)

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

            # Get the associated token accounts
            source_token_account = get_associated_token_address(
                sender_pubkey, token_mint_pubkey
            )
            destination_token_account = get_associated_token_address(
                recipient_pubkey, token_mint_pubkey
            )

            # Get token decimals
            token_info = solana_client.get_token_supply(token_mint_pubkey)
            decimals = 0
            if hasattr(token_info, "value"):
                decimals = token_info.value.decimals
            else:
                decimals = token_info["result"]["value"]["decimals"]

            # Calculate token amount with decimals
            token_amount = int(amount * (10**decimals))

            # Check token balance
            source_balance_info = solana_client.get_token_account_balance(
                source_token_account
            )
            source_balance = 0
            if hasattr(source_balance_info, "value"):
                source_balance = int(source_balance_info.value.amount)
            else:
                source_balance = int(source_balance_info["result"]["value"]["amount"])

            if source_balance < token_amount:
                return f"Insufficient token balance. Wallet has {source_balance / (10**decimals)} tokens."

            # Check if destination account exists
            dest_account_info = solana_client.get_account_info(
                destination_token_account
            )
            destination_exists = False
            if hasattr(dest_account_info, "value"):
                destination_exists = dest_account_info.value is not None
            else:
                destination_exists = dest_account_info["result"]["value"] is not None

            # Get latest blockhash
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

            # Create instructions
            instructions = []

            # Create destination account if needed
            if not destination_exists:
                create_account_ix = create_associated_token_account(
                    payer=sender_pubkey, owner=recipient_pubkey, mint=token_mint_pubkey
                )
                instructions.append(create_account_ix)

            # Create transfer instruction
            # Token transfer instruction (3 = transfer)
            transfer_data = bytes([3]) + struct.pack("<Q", token_amount)

            transfer_ix = TransactionInstruction(
                program_id=TOKEN_PROGRAM_ID,
                data=transfer_data,
                accounts=[
                    AccountMeta(
                        pubkey=source_token_account, is_signer=False, is_writable=True
                    ),
                    AccountMeta(
                        pubkey=destination_token_account,
                        is_signer=False,
                        is_writable=True,
                    ),
                    AccountMeta(
                        pubkey=sender_pubkey, is_signer=True, is_writable=False
                    ),
                ],
            )

            instructions.append(transfer_ix)

            # Create transaction (similar to SOL send)
            msg = MessageV0.try_compile(
                payer=sender_pubkey,
                instructions=instructions,
                address_lookup_table_accounts=[],
                recent_blockhash=blockhash,
            )

            tx = VersionedTransaction(msg, [keypair])
            serialized_tx = bytes(tx)

            # Send transaction
            send_response = solana_client.send_raw_transaction(serialized_tx)

            # Get signature
            if hasattr(send_response, "value"):
                signature = str(send_response.value)
            else:
                signature = send_response["result"]

            explorer_url = f"https://solscan.io/tx/{signature}"
            return f"Transaction was successfully sent, transaction hash is {signature}, you can view the txn details at {explorer_url}"

        except Exception as e:
            logger.error(f"[LUMOKIT] Error sending SPL tokens: {str(e)}")
            return f"Failed to send SPL tokens: {str(e)}"

    def _run(
        self,
        agent_public: str,
        agent_private: str,
        recipient_address: str,
        token_address: str,
        amount: float,
    ) -> str:
        """Synchronous version returns a message instead of raising an error."""
        return "This tool only supports asynchronous execution. Please use the async version instead."


#################################################
#### SOLANA BURN TOKEN TOOL ####
#################################################


class SolanaBurnTokenInput(BaseModel):
    """Input for the Solana Burn Token tool."""

    agent_public: str = Field(
        ..., description="Public key of the agent wallet to burn tokens from"
    )
    agent_private: str = Field(
        ..., description="Encrypted private key of the agent wallet"
    )
    token_address: str = Field(
        ..., description="SPL token address (mint address) of the token to burn"
    )
    amount: float = Field(..., description="Amount of tokens to burn")


class SolanaBurnTokenTool(BaseTool):
    """Tool for burning SPL tokens from a wallet."""

    name: ClassVar[str] = "solana_burn_token_tool"
    description: ClassVar[str] = (
        "Burn SPL tokens from agent wallet, permanently removing them from circulation."
    )
    args_schema: ClassVar[Type[BaseModel]] = SolanaBurnTokenInput

    async def _arun(
        self, agent_public: str, agent_private: str, token_address: str, amount: float
    ) -> str:
        """Execute the Solana SPL token burn asynchronously."""
        try:
            logger.info(
                f"[LUMOKIT] Solana Burn Token initiated: {agent_public} burning token {token_address}"
            )

            # Basic validation
            if amount <= 0:
                return "Amount must be greater than 0."

            # Clean up addresses
            agent_public = agent_public.strip()
            token_address = token_address.strip()

            # Parse addresses
            owner_pubkey = Pubkey.from_string(agent_public)
            token_mint_pubkey = Pubkey.from_string(token_address)

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

            # Get the associated token account
            token_account = get_associated_token_address(
                owner_pubkey, token_mint_pubkey
            )

            # Get token decimals
            token_info = solana_client.get_token_supply(token_mint_pubkey)
            decimals = 0
            if hasattr(token_info, "value"):
                decimals = token_info.value.decimals
            else:
                decimals = token_info["result"]["value"]["decimals"]

            # Calculate token amount with decimals
            token_amount = int(amount * (10**decimals))

            # Check token balance
            token_balance_info = solana_client.get_token_account_balance(token_account)
            token_balance = 0
            if hasattr(token_balance_info, "value"):
                token_balance = int(token_balance_info.value.amount)
            else:
                token_balance = int(token_balance_info["result"]["value"]["amount"])

            if token_balance < token_amount:
                return f"Insufficient token balance. Wallet has {token_balance / (10**decimals)} tokens."

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

            # Create burn instruction
            # Token burn instruction (8 = burn)
            burn_data = bytes([8]) + struct.pack("<Q", token_amount)

            burn_ix = TransactionInstruction(
                program_id=TOKEN_PROGRAM_ID,
                data=burn_data,
                accounts=[
                    AccountMeta(
                        pubkey=token_account, is_signer=False, is_writable=True
                    ),
                    AccountMeta(
                        pubkey=token_mint_pubkey, is_signer=False, is_writable=True
                    ),
                    AccountMeta(pubkey=owner_pubkey, is_signer=True, is_writable=False),
                ],
            )

            # Create transaction
            msg = MessageV0.try_compile(
                payer=owner_pubkey,
                instructions=[burn_ix],
                address_lookup_table_accounts=[],
                recent_blockhash=blockhash,
            )

            tx = VersionedTransaction(msg, [keypair])
            serialized_tx = bytes(tx)

            # Send transaction
            send_response = solana_client.send_raw_transaction(serialized_tx)

            # Get the transaction signature
            if hasattr(send_response, "value"):
                signature = str(send_response.value)
            else:
                signature = send_response["result"]

            explorer_url = f"https://solscan.io/tx/{signature}"
            return f"Transaction was successfully sent, transaction hash is {signature}, you can view the txn details at {explorer_url}"

        except Exception as e:
            logger.error(f"[LUMOKIT] Error burning tokens: {str(e)}")
            return f"Failed to burn tokens: {str(e)}"

    def _run(
        self, agent_public: str, agent_private: str, token_address: str, amount: float
    ) -> str:
        """Synchronous version returns a message instead of raising an error."""
        return "This tool only supports asynchronous execution. Please use the async version instead."

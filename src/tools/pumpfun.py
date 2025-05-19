import base64
import io
import json
import re
import struct
import urllib.parse
from typing import ClassVar, Type

import base58
import requests
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from solana.rpc.api import Client
from solders.commitment_config import CommitmentLevel
from solders.hash import Hash
from solders.instruction import AccountMeta
from solders.instruction import Instruction as TransactionInstruction
from solders.keypair import Keypair
from solders.message import MessageV0
from solders.pubkey import Pubkey
from solders.rpc.config import RpcSendTransactionConfig
from solders.rpc.requests import SendVersionedTransaction
from solders.system_program import TransferParams, transfer
from solders.transaction import VersionedTransaction
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import (create_associated_token_account,
                                    get_associated_token_address)

from helper.decrypt_private import WalletDecryptor
from settings.config import CONFIG
from settings.logger import logger

#################################################
#### PUMP.FUN LAUNCH COIN TOOL ####
#################################################


class PumpFunLaunchCoinInput(BaseModel):
    """Input for the Pump.Fun Launch Coin tool."""

    agent_public: str = Field(
        ..., description="Public key of the agent wallet to create the token from"
    )
    agent_private: str = Field(
        ..., description="Encrypted private key of the agent wallet"
    )
    token_name: str = Field(..., description="Name of the token to launch")
    token_symbol: str = Field(..., description="Symbol/ticker of the token")
    description: str = Field(..., description="Description of the token")
    twitter_url: str = Field(None, description="Twitter URL for the token (optional)")
    telegram_url: str = Field(None, description="Telegram URL for the token (optional)")
    website: str = Field(None, description="Website URL for the token (optional)")
    image_url: str = Field(..., description="URL to the image for the token")
    amount: float = Field(
        0.0, description="Amount of SOL to buy for the token (default is 0)"
    )


class PumpFunLaunchCoinTool(BaseTool):
    """Tool for launching a new token on Pump.fun platform."""

    name: ClassVar[str] = "pumpfun_launch_coin_tool"
    description: ClassVar[str] = (
        "Launch a new token on Pump.fun platform. Requires token details and agent wallet information."
    )
    args_schema: ClassVar[Type[BaseModel]] = PumpFunLaunchCoinInput

    async def _arun(
        self,
        agent_public: str,
        agent_private: str,
        token_name: str,
        token_symbol: str,
        description: str,
        twitter_url: str = None,
        telegram_url: str = None,
        website: str = None,
        image_url: str = None,
        amount: float = 0.0,
    ) -> str:
        """Launch a token on Pump.fun asynchronously."""
        try:
            logger.info(
                f"[LUMOKIT] Initiating Pump.Fun token launch for: {token_name} ({token_symbol})"
            )

            # Basic validation
            if not token_name or not token_symbol or not description or not image_url:
                return "Token name, symbol, description, and image URL are required."

            # Validate URLs if provided
            url_validators = {
                "Twitter URL": twitter_url,
                "Telegram URL": telegram_url,
                "Website": website,
                "Image URL": image_url,
            }

            for url_type, url in url_validators.items():
                if url and not self._is_valid_url(url):
                    return f"Invalid {url_type}: {url}. Please provide a valid URL."

            # Validate SOL amount
            if amount < 0:
                return "Amount to buy must be greater than or equal to 0."

            # Clean up addresses
            agent_public = agent_public.strip()

            # Decrypt private key and create keypair
            try:
                decrypted_key = await WalletDecryptor.decrypt_wallet(agent_private)
                private_key_bytes = base58.b58decode(decrypted_key)

                if len(private_key_bytes) == 64:
                    signer_keypair = Keypair.from_bytes(private_key_bytes)
                else:
                    signer_keypair = Keypair.from_seed(private_key_bytes)

                # Simple check that the key is correct
                if str(signer_keypair.pubkey()) != agent_public:
                    return "Public key mismatch. The private key doesn't match the provided public key."
            except Exception as e:
                logger.error(f"[LUMOKIT] Error with private key: {str(e)}")
                return f"Error with private key: {str(e)}"

            # Generate a random keypair for the token mint
            mint_keypair = Keypair()

            # Prepare token metadata
            form_data = {
                "name": token_name,
                "symbol": token_symbol,
                "description": description,
                "showName": "true",
            }

            # Add optional fields if provided
            if twitter_url:
                form_data["twitter"] = twitter_url
            if telegram_url:
                form_data["telegram"] = telegram_url
            if website:
                form_data["website"] = website

            # Fetch and prepare the image
            try:
                image_response = requests.get(image_url)
                image_response.raise_for_status()
                image_content = image_response.content

                # Attempt to determine content type from URL
                content_type = self._get_content_type_from_url(image_url)
                if not content_type:
                    content_type = "image/jpeg"  # Default assumption

                # Get filename from URL or use default
                filename = self._get_filename_from_url(image_url) or "token_image.jpg"

                files = {"file": (filename, image_content, content_type)}
            except Exception as e:
                logger.error(f"[LUMOKIT] Error fetching image: {str(e)}")
                return f"Failed to fetch image from URL: {str(e)}"

            # Create IPFS metadata storage
            try:
                metadata_response = requests.post(
                    "https://pump.fun/api/ipfs", data=form_data, files=files
                )
                metadata_response.raise_for_status()
                metadata_response_json = metadata_response.json()

                if "metadataUri" not in metadata_response_json:
                    return "Failed to create token metadata: No metadata URI returned from server."

                # Token metadata
                token_metadata = {
                    "name": token_name,
                    "symbol": token_symbol,
                    "uri": metadata_response_json["metadataUri"],
                }
            except Exception as e:
                logger.error(f"[LUMOKIT] Error creating token metadata: {str(e)}")
                return f"Failed to create token metadata: {str(e)}"

            # Generate the create transaction
            try:
                create_response = requests.post(
                    "https://pumpportal.fun/api/trade-local",
                    headers={"Content-Type": "application/json"},
                    data=json.dumps(
                        {
                            "publicKey": str(signer_keypair.pubkey()),
                            "action": "create",
                            "tokenMetadata": token_metadata,
                            "mint": str(mint_keypair.pubkey()),
                            "denominatedInSol": "true",
                            "amount": amount,
                            "slippage": 10,
                            "priorityFee": 0.0005,
                            "pool": "pump",
                        }
                    ),
                )
                create_response.raise_for_status()

                # Parse the transaction bytes
                tx_bytes = create_response.content
                if not tx_bytes:
                    return "Failed to generate transaction: Empty response from server."

                # Create the versioned transaction with signatures
                original_tx = VersionedTransaction.from_bytes(tx_bytes)
                tx = VersionedTransaction(
                    original_tx.message, [mint_keypair, signer_keypair]
                )

                # Configure the transaction sending
                commitment = CommitmentLevel.Confirmed
                config = RpcSendTransactionConfig(preflight_commitment=commitment)
                tx_payload = SendVersionedTransaction(tx, config)

                # Send the transaction
                send_response = requests.post(
                    url=CONFIG.SOLANA_RPC_URL,
                    headers={"Content-Type": "application/json"},
                    data=tx_payload.to_json(),
                )
                send_response.raise_for_status()

                send_result = send_response.json()
                if "result" not in send_result:
                    return f"Transaction failed: {json.dumps(send_result.get('error', 'Unknown error'))}"

                tx_signature = send_result["result"]
                explorer_url = f"https://solscan.io/tx/{tx_signature}"

                logger.info(f"[LUMOKIT] Token successfully created: {tx_signature}")

                return f"Token successfully created! Transaction hash is {tx_signature}, you can view the txn details at {explorer_url}"

            except Exception as e:
                logger.error(f"[LUMOKIT] Error launching token: {str(e)}")
                return f"Failed to launch token: {str(e)}"

        except Exception as e:
            logger.error(f"[LUMOKIT] General error in token launch process: {str(e)}")
            return f"An error occurred during the token launch process: {str(e)}"

    def _run(
        self,
        agent_public: str,
        agent_private: str,
        token_name: str,
        token_symbol: str,
        description: str,
        twitter_url: str = None,
        telegram_url: str = None,
        website: str = None,
        image_url: str = None,
        amount: float = 0.0,
    ) -> str:
        """Synchronous version returns a message instead of raising an error."""
        return "This tool only supports asynchronous execution. Please use the async version instead."

    def _is_valid_url(self, url: str) -> bool:
        """Validate if a string is a properly formatted URL."""
        if not url:
            return True  # Empty URLs are considered valid (for optional fields)

        regex = re.compile(
            r"^(?:http|https)://"  # http:// or https://
            r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # domain
            r"localhost|"  # localhost
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # or IPv4
            r"(?::\d+)?"  # optional port
            r"(?:/?|[/?]\S+)$",
            re.IGNORECASE,
        )

        return bool(regex.match(url))

    def _get_content_type_from_url(self, url: str) -> str:
        """Try to determine content type from URL extension."""
        # Extract file extension from URL
        path = urllib.parse.urlparse(url).path
        ext = path.split(".")[-1].lower() if "." in path else ""

        # Map common extensions to content types
        content_types = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "webp": "image/webp",
            "svg": "image/svg+xml",
        }

        return content_types.get(ext, "")

    def _get_filename_from_url(self, url: str) -> str:
        """Extract filename from URL."""
        path = urllib.parse.urlparse(url).path
        return path.split("/")[-1] if "/" in path else ""

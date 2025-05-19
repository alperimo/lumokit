import base64

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from settings.config import CONFIG
from settings.logger import logger


async def derive_key_from_salt() -> bytes:
    """
    Derives a Fernet key from the salt in CONFIG
    """
    try:
        salt = CONFIG.WALLET_ENCRYPTION_SALT
        salt_bytes = salt.encode("utf-8")

        # Use PBKDF2 to derive a secure key from the salt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt_bytes,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(salt_bytes))
        return key
    except Exception as e:
        logger.error(f"[LUMOKIT] Error deriving key: {str(e)}")
        raise ValueError("Failed to derive encryption key")


async def decrypt_private_key(encrypted_key: str) -> str:
    """
    Decrypts an encrypted private key using the salt from config

    Args:
        encrypted_key (str): The encrypted private key to decrypt

    Returns:
        str: The decrypted private key string

    Raises:
        ValueError: If decryption fails
    """
    try:
        # Trim whitespace from input
        encrypted_key = encrypted_key.strip()

        # Derive the key from the salt in CONFIG
        key = await derive_key_from_salt()
        f = Fernet(key)

        # Handle base64 padding if needed
        padded_key = encrypted_key
        if len(encrypted_key) % 4 != 0:
            padded_key = encrypted_key + "=" * (-len(encrypted_key) % 4)

        # Decode and decrypt
        encrypted_data = base64.urlsafe_b64decode(padded_key)
        decrypted_data = f.decrypt(encrypted_data)

        # Return decoded result
        return decrypted_data.decode("utf-8")

    except Exception as e:
        logger.error(f"[LUMOKIT] Error decrypting private key: {str(e)}")
        raise ValueError("Failed to decrypt private key")


class WalletDecryptor:
    """
    A class to handle wallet decryption operations
    """

    @staticmethod
    async def decrypt_wallet(encrypted_key: str) -> str:
        """
        Decrypts a wallet's private key

        Args:
            encrypted_key (str): The encrypted private key

        Returns:
            str: The decrypted private key
        """
        return await decrypt_private_key(encrypted_key)

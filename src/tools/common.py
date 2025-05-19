import json
from typing import ClassVar, Dict, Optional, Type

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from api.users.controllers import get_wallet_portfolio_ds
from settings.logger import logger

#################################################
#### WALLET PORTFOLIO TOOL ####
#################################################


class WalletPortfolioInput(BaseModel):
    """Input for the wallet portfolio tool."""

    agent_public: Optional[str] = Field(
        None, description="The public key of the wallet to check"
    )


class WalletPortfolioTool(BaseTool):
    """Tool for retrieving a wallet's token portfolio from BirdEye."""

    name: ClassVar[str] = "wallet_portfolio_tool"
    description: ClassVar[str] = (
        "Get detailed information about all tokens held in a wallet. Useful when you need to check a user's current token balances."
    )
    args_schema: ClassVar[Type[BaseModel]] = WalletPortfolioInput

    async def _arun(self, agent_public: Optional[str] = None) -> str:
        """Execute the wallet portfolio lookup."""
        try:
            # Check if a wallet address was provided
            if not agent_public:
                logger.info(
                    "[LUMOKIT] Wallet portfolio tool called without a wallet address"
                )
                return "User has not added a wallet yet."

            # Call the API to get portfolio data - use the direct Solana RPC function
            logger.info(
                f"[LUMOKIT] Fetching wallet portfolio for address: {agent_public}"
            )
            portfolio_data = await get_wallet_portfolio_ds(agent_public)

            # Check if the API call was successful
            if not portfolio_data.get("success", False):
                logger.error(
                    f"[LUMOKIT] Error fetching portfolio: {portfolio_data.get('error', 'Unknown error')}"
                )
                return "There is an error while getting the user's balances."

            # Extract token list and wallet address
            data = portfolio_data.get("data", {})
            wallet_address = data.get("wallet", "Unknown Wallet")
            tokens = data.get("items", [])
            total_value = data.get("totalUsd", 0)

            # If no tokens found
            if not tokens:
                logger.info(f"[LUMOKIT] No tokens found for wallet: {agent_public}")
                return "User has no SOL balance, 0."

            # Filter tokens with value above 0.2 USD
            min_value_usd = 0.2
            significant_tokens = [
                token for token in tokens if token.get("valueUsd", 0) >= min_value_usd
            ]

            if not significant_tokens:
                # If no significant tokens, include at least the largest token by value
                if tokens:
                    tokens.sort(key=lambda x: x.get("valueUsd", 0), reverse=True)
                    significant_tokens = [tokens[0]]

            # Format the output
            output_lines = [f"Wallet Portfolio for {wallet_address}:"]

            # Add significant tokens
            for token in significant_tokens:
                token_name = token.get("name", token.get("symbol", "Unknown Token"))
                token_symbol = token.get("symbol", "???")
                token_address = token.get("address", "Unknown Address")
                token_amount = token.get("uiAmount", 0)  # Use formatted amount
                token_usd_value = token.get("valueUsd", 0)
                token_price = token.get("priceUsd", 0)

                # Format as a readable line with more details
                token_line = (
                    f"• {token_name} ({token_symbol}): {token_amount:,.4f} tokens\n"
                    f"  Value: ${token_usd_value:,.2f} USD (Price: ${token_price:,.6f} per token)\n"
                    f"  Address: {token_address}"
                )
                output_lines.append(token_line)

            # Count and summarize low-value tokens
            low_value_tokens = [
                t for t in tokens if t.get("valueUsd", 0) < min_value_usd
            ]
            low_value_count = len(low_value_tokens)
            low_value_total = sum(t.get("valueUsd", 0) for t in low_value_tokens)

            if low_value_count > 0:
                output_lines.append(
                    f"\nAdditionally, you have {low_value_count} tokens worth less than ${min_value_usd} "
                    f"(total value: ${low_value_total:,.2f})."
                )

            # Add total portfolio value
            if total_value:
                output_lines.append(f"\nTotal Portfolio Value: ${total_value:,.2f} USD")

            return "\n".join(output_lines)

        except Exception as e:
            logger.error(f"[LUMOKIT] Error in wallet portfolio tool: {str(e)}")
            return "There is an error while getting the user's balances."

    def _run(self, agent_public: Optional[str] = None) -> str:
        """Synchronous version not implemented."""
        raise NotImplementedError("This tool only supports async execution.")


#################################################
#### TOKEN IDENTIFICATION TOOL ####
#################################################


class TokenIdentificationInput(BaseModel):
    """Input for the token identification tool."""

    identifier: str = Field(
        ...,
        description="The token name or ticker to search for (e.g., 'Raydium', 'RAY', '$RAY')",
    )


class TokenIdentificationTool(BaseTool):
    """Tool for identifying token information by name or ticker."""

    name: ClassVar[str] = "token_identification_tool"
    description: ClassVar[str] = (
        "Get token information by name or ticker. Useful when you need to find the contract address for a token."
    )
    args_schema: ClassVar[Type[BaseModel]] = TokenIdentificationInput

    # Token data dictionary
    TOKEN_DATA: ClassVar[Dict[str, Dict[str, str]]] = {
        "Tether": {
            "ticker": "USDT",
            "contract_address": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
        },
        "USDC": {
            "ticker": "USDC",
            "contract_address": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        },
        "USDS": {
            "ticker": "USDS",
            "contract_address": "USDSwr9ApdHk5bvJKMjzff41FfuX8bSxdKcR81vTwcA",
        },
        "Ethena USDe": {
            "ticker": "USDe",
            "contract_address": "DEkqHyPN7GMRJ5cArtQFAWefqbZb33Hyf6s5iCwjEonT",
        },
        "Coinbase Wrapped BTC": {
            "ticker": "cbBTC",
            "contract_address": "cbbtcf3aa214zXHbiAZQwf4122FBYbraNdFqgw4iMij",
        },
        "BlackRock USD Institutional Digital Liquidity Fund": {
            "ticker": "BUILD",
            "contract_address": "GyWgeqpy5GueU2YbkE8xqUeVEokCMMCEeUrfbtMw6phr",
        },
        "Official Trump": {
            "ticker": "TRUMP",
            "contract_address": "6p6xgHyF7AeE6TZkSmFsko444wqoP15icUSqi2jfGiPN",
        },
        "Render": {
            "ticker": "RENDER",
            "contract_address": "rndrizKT3MK1iimdxRdWabcF7Zg7AR5T4nud4EkHBof",
        },
        "Jupiter Perpetuals Liquidity Provider Token": {
            "ticker": "JLP",
            "contract_address": "27G8MtK7VtTcCHkpASjSDdkWWYfoqT6ggEuKidVJidD4",
        },
        "Binance Staked SOL": {
            "ticker": "BNSOL",
            "contract_address": "BNso1VUJnh4zcfpZa6986Ea66P6TCp59hvtNJ8b1X85",
        },
        "Bonk": {
            "ticker": "Bonk",
            "contract_address": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
        },
        "Fartcoin": {
            "ticker": "Fartcoin",
            "contract_address": "9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump",
        },
        "PayPal USD": {
            "ticker": "PYUSD",
            "contract_address": "2b1kV6DkPAnxd5ixfnxCpjxmKwqjjaYmCZfHsFu24GXo",
        },
        "Jupiter Staked SOL": {
            "ticker": "JupSOL",
            "contract_address": "jupSoLaHXQiZZTSfEWMTRRgpnyFm8f6sZdosWBjx93v",
        },
        "Marinade Staked SOL": {
            "ticker": "mSOL",
            "contract_address": "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",
        },
        "Raydium": {
            "ticker": "RAY",
            "contract_address": "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",
        },
        "Helium": {
            "ticker": "HNT",
            "contract_address": "hntyVP6YFm1Hg25TN9WGLqM12b8TQmcknKrdu1oxWux",
        },
        "Ondo US Dollar Yield": {
            "ticker": "USDY",
            "contract_address": "A1KLoBrKBde8Ty9qtNQUtq3C2ortoC3u7twggz7sEto6",
        },
        "Jito": {
            "ticker": "JTO",
            "contract_address": "jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL",
        },
        "Pyth Network": {
            "ticker": "PYTH",
            "contract_address": "HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3",
        },
        "dogwifhat": {
            "ticker": "WIF",
            "contract_address": "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
        },
        "Solayer": {
            "ticker": "LAYER",
            "contract_address": "LAYER4xPpTCb3QL8S9u41EAhAX7mhBn8Q6xMTwY2Yzc",
        },
        "SPX6900": {
            "ticker": "SPX",
            "contract_address": "J3NKxxXZcnNiMjKw9hYb2K4LUxgwB6t1FtPtQVsv3KFr",
        },
        "Grass": {
            "ticker": "GRASS",
            "contract_address": "Grass7B4RdKfBCjTKgSqnXkqjwiGvQyFbuSCUJr3XXjs",
        },
        "Virtuals Protocol": {
            "ticker": "VIRTUAL",
            "contract_address": "3iQL8BFS2vE7mww4ehAqQHAsbmRNCrPxizWAT2Zfyr9y",
        },
        "OUSG": {
            "ticker": "OUSG",
            "contract_address": "i7u4r16TcsJTgq1kAG8opmVZyVnAKBwLKu6ZPMwzxNc",
        },
        "tBTC": {
            "ticker": "TBTC",
            "contract_address": "6DNSN2BJsaPFdFFc1zP37kkeNe4Usc1Sqkzr9C9vPWcU",
        },
        "Pudgy Penguins": {
            "ticker": "PENGU",
            "contract_address": "2zMMhcVQEXDtdE6vsFS7S7D5oUodfJHE8vd1gnBouauv",
        },
        "Wormhole": {
            "ticker": "W",
            "contract_address": "85VBFQZC9TZkfaptBWjvUw7YbZjy52A6mjtPGjstQAmQ",
        },
        "Popcat": {
            "ticker": "POPCAT",
            "contract_address": "7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr",
        },
        "Saros": {
            "ticker": "SAROS",
            "contract_address": "SarosY6Vscao718M4A778z4CGtvcwcGef5M9MEH1LGL",
        },
        "Global Dollar": {
            "ticker": "USDG",
            "contract_address": "2u1tszSeqZ3qBWF3uNGPFc8TzMk2tdiwknnRMWGWjGWH",
        },
        "Aethir": {
            "ticker": "ATH",
            "contract_address": "Dm5BxyMetG3Aq5PaG1BrG7rBYqEMtnkjvPNMExfacVk7",
        },
        "cat in a dogs world": {
            "ticker": "MEW",
            "contract_address": "MEW1gQWJ3nEXg2qgERiKu7FAFj79PHvQVREQUzScPP5",
        },
        "EURC": {
            "ticker": "EURC",
            "contract_address": "HzwqbKZw8HxMN6bF2yFZNrht3c2iXXzpKcFu7uBEDKtr",
        },
        "Baby Doge Coi": {
            "ticker": "BabyDoge",
            "contract_address": "7dUKUopcNWW6CcU4eRxCHh1uiMh32zDrmGf6ufqhxann",
        },
        "SwissBorg": {
            "ticker": "BORG",
            "contract_address": "3dQTr7ror2QPKQ3GbBCokJUmjErGg8kTJzdnYjNfvi3Z",
        },
        "Basic Attentio": {
            "ticker": "BAT",
            "contract_address": "EPeUFDgHRxs9xxEPVaL6kfGQvCon7jmAWKVUHuux1Tpz",
        },
        "Drift Staked SOL": {
            "ticker": "dSOL",
            "contract_address": "Dso1bDeDjCQxTrWHqUUi63oBvV7Mdm6WaobLbQ7gnPQ",
        },
        "Bybit Staked SOL": {
            "ticker": "bbSOL",
            "contract_address": "Bybit2vBJGhPF52GBdNaQfUJ6ZpThSgHBobjWZpLPb4B",
        },
        "CHEX Token": {
            "ticker": "CHEX",
            "contract_address": "6dKCoWjpj5MFU5gWDEFdpUUeBasBLK3wLEwhUzQPAa1e",
        },
        "Frax Share": {
            "ticker": "FXS",
            "contract_address": "6LX8BhMQ4Sy2otmAWj7Y5sKd9YTVVUgfMsBzT6B9W7ct",
        },
        "ai16z": {
            "ticker": "ai16z",
            "contract_address": "HeLp6NuQkmYB4pYWo2zYs22mESHXPQYzXbB8n4V98jwC",
        },
        "Gigachad": {
            "ticker": "GIGA",
            "contract_address": "63LfDmNb3MQ8mw9MtZ2To9bEA2M71kZUUGq5tiJxcqj9",
        },
        "Threshold Networ": {
            "ticker": "T",
            "contract_address": "4Njvi3928U3figEF5tf8xvjLC5GqUN33oe4XTJNe7xXC",
        },
        "Melania Meme": {
            "ticker": "MELANIA",
            "contract_address": "FUAfBo2jgks6gB4Z4LfZkqSZgzNucisEHqnNebaRxM1P",
        },
        "Alchemist AI": {
            "ticker": "ALCH",
            "contract_address": "HNg5PYJmtqcmzXrv6S9zP1CDKk5BgDuyFBxbvNApump",
        },
        "Dog (Bitcoin)": {
            "ticker": "DOG",
            "contract_address": "dog1viwbb2vWDpER5FrJ4YFG6gq6XuyFohUe9TXN65u",
        },
        "Metaplex": {
            "ticker": "MPLX",
            "contract_address": "METAewgxyPbgwsseH8T16a39CQ5VyVxZi9zXiDPY18m",
        },
        "ORDI": {
            "ticker": "ORDI",
            "contract_address": "u9nmK5sQovm6ACVCQbbq8xUMpFqdPSYxdxVwXUX4sjY",
        },
        "Goatseus Maximus": {
            "ticker": "GOAT",
            "contract_address": "CzLSujWBLFsSjncfkh59rUFqvafWcY5tzedWJSuypump",
        },
        "Act I : The AI Prophecy": {
            "ticker": "ACT",
            "contract_address": "GJAFwWjJ3vnTsrQVabjBVK2TYB1YtRCQXRDfDgUnpump",
        },
        "test griffain.com": {
            "ticker": "GRIFFAIN",
            "contract_address": "KENJSUYLASHUMfHyy5o4Hp2FdNqZg1AsUPhfH2kYvEP",
        },
        "AI Rig Complex": {
            "ticker": "ARC",
            "contract_address": "61V8vBaqAGMpgDQi4JcAwo1dmBGHsyhzodcPqnEVpump",
        },
        "Ava AI": {
            "ticker": "AVA",
            "contract_address": "DKu9kykSfbN5LBfFXtNNDPaX35o4Fv6vJ9FKk7pZpump",
        },
        "swarms": {
            "ticker": "swarms",
            "contract_address": "74SBV4zDXxTRgv1pEMoECskKBkZHc2yGPnc7GYVepump",
        },
        "BAYC AI": {
            "ticker": "BAYC",
            "contract_address": "ArUyEVWGCzZMtAxcPmNH8nDFZ4kMjxrMbpsQf3NEpump",
        },
        "SwarmNode.ai": {
            "ticker": "SNAI",
            "contract_address": "Hjw6bEcHtbHGpQr8onG3izfJY5DJiWdt7uk2BfdSpump",
        },
        "PYTHIA": {
            "ticker": "PYTHIA",
            "contract_address": "CreiuhfwdWCN5mJbMJtA9bBpYQrQF2tCBuZwSPWfpump",
        },
        "Moby AI": {
            "ticker": "MOBY",
            "contract_address": "Cy1GS2FqefgaMbi45UunrUzin1rfEmTUYnomddzBpump",
        },
        "AGiXT": {
            "ticker": "AGiXT",
            "contract_address": "F9TgEJLLRUKDRF16HgjUCdJfJ5BK6ucyiW8uJxVPpump",
        },
        "yesnoerror": {
            "ticker": "YNE",
            "contract_address": "7D1iYWfhw2cr9yBZBFE6nZaaSUvXHqG5FizFFEZwpump",
        },
        "Lumo-8B-Instruct": {
            "ticker": "LUMO",
            "contract_address": "4FkNq8RcCYg4ZGDWh14scJ7ej3m5vMjYTcWoJVkupump",
        },
        "DOGE AI": {
            "ticker": "DOGEAI",
            "contract_address": "9UYAYvVS2cZ3BndbsoG1ScJbjfwyEPGxjE79hh5ipump",
        },
        "XSPA": {
            "ticker": "XSPA",
            "contract_address": "8Hg96R1AGDe5vKABwniVPT2LHdhZHmCTFijZAXXZpump",
        },
        "Hive AI": {
            "ticker": "BUZZ",
            "contract_address": "9DHe3pycTuymFk4H4bbPoAJ4hQrr2kaLDF6J6aAKpump",
        },
        "Autonome": {
            "ticker": "AUTO",
            "contract_address": "2Yufe8mbyi75Zrye56KYz7CVKoX7oCtDZRksd8tQpump",
        },
        "Kolin": {
            "ticker": "KOLIN",
            "contract_address": "4q3Z58YxrZEAVMLtMwnm7eHtodSD3LSpSNt3pDnqpump",
        },
        "ViralMind": {
            "ticker": "VIRAL",
            "contract_address": "HW7D5MyYG4Dz2C98axfjVBeLWpsEnofrqy6ZUwqwpump",
        },
        "nuit": {
            "ticker": "nuit",
            "contract_address": "2eXamy7t3kvKhfV6aJ6Uwe3eh8cuREFcTKs1mFKZpump",
        },
        "Stargate": {
            "ticker": "Stargate",
            "contract_address": "6WMCsn47LujngJz42foVFoaXjSeVZFWwLaSMUAZfpump",
        },
        "George Droyd": {
            "ticker": "FLOYDAI",
            "contract_address": "J7tYmq2JnQPvxyhcXpCDrvJnc9R5ts8rv7tgVHDPsw7U",
        },
        "Claude Opus": {
            "ticker": "OPUS",
            "contract_address": "9JhFqCA21MoAXs2PTaeqNQp2XngPn1PgYr2rsEVCpump",
        },
        "Lea AI": {
            "ticker": "LEA",
            "contract_address": "8SpPaFLycx897D6sowPZkEkcNdDahzRZb5itr6D8pump",
        },
        "listen-rs": {
            "ticker": "listen",
            "contract_address": "Cn5Ne1vmR9ctMGY9z5NC71A3NYFvopjXNyxYtfVYpump",
        },
        "MAX": {
            "ticker": "MAX",
            "contract_address": "oraim8c9d1nkfuQk9EzGYEUGxqL3MHQYndRw1huVo5h",
        },
        "Shoggoth": {
            "ticker": "Shoggoth",
            "contract_address": "H2c31USxu35MDkBrGph8pUDUnmzo2e4Rf4hnvL2Upump",
        },
        "Degen Spartan AI": {
            "ticker": "degenai",
            "contract_address": "Gu3LDkn7Vx3bmCzLafYNKcDxv2mH7YN44NJZFXnypump",
        },
        "Dasha": {
            "ticker": "vvaifu",
            "contract_address": "FQ1tyso61AH1tzodyJfSwmzsD3GToybbRNoZxUBz21p8",
        },
        "TOP HAT": {
            "ticker": "HAT",
            "contract_address": "AxGAbdFtdbj2oNXa4dKqFvwHzgFtW9mFHWmd7vQfpump",
        },
        "RekaAI": {
            "ticker": "RekaAI",
            "contract_address": "BNvBamkiAbGoeQUsVpE5dUega6e3X1SUHu5DRqESEnG7",
        },
        "AgentiPy": {
            "ticker": "APY",
            "contract_address": "yLUD35WTiPLEY6DUqEj5W2JVXF2DfKB5arPkKJXpump",
        },
        "Aimonica Brands": {
            "ticker": "Aimonica",
            "contract_address": "FVdo7CDJarhYoH6McyTFqx71EtzCPViinvdd1v86Qmy5",
        },
        "Eliza": {
            "ticker": "ELIZA",
            "contract_address": "5voS9evDjxF589WuEub5i4ti7FWQmZCsAsyD5ucbuRqM",
        },
        "neur.sh": {
            "ticker": "NEUR",
            "contract_address": "3N2ETvNpPNAxhcaXgkhKoY1yDnQfs41Wnxsx5qNJpump",
        },
        "Glades": {
            "ticker": "GLDS",
            "contract_address": "6uYAMiY8KwDsW9ome5AvadsnNUKF19Evz4QxQ43Dpump",
        },
        "TRI SIGMA": {
            "ticker": "TRISIG",
            "contract_address": "BLDiYcvm3CLcgZ7XUBPgz6idSAkNmWY6MBbm8Xpjpump",
        },
        "Memes AI": {
            "ticker": "MemesAI",
            "contract_address": "39qibQxVzemuZTEvjSB7NePhw9WyyHdQCqP8xmBMpump",
        },
        "MAIAR": {
            "ticker": "MAIAR",
            "contract_address": "G5e2XonmccmdKc98g3eNQe5oBYGw9m8xdMUvVtcZpump",
        },
        "SamurAI": {
            "ticker": "SamurAI",
            "contract_address": "J7HK78Aad2GgWZFvfF1ErhU7jUT5AKPpU41miMaypump",
        },
        "Aria": {
            "ticker": "ARIA",
            "contract_address": "GhBPHgnNF99EThYxt4bxUfPX1hCPyAS72RCBgLjLpump",
        },
        "chAtoshI": {
            "ticker": "CHATOSHI",
            "contract_address": "Bhu2wBWxfWkRJ6pFn5NodnEvMCqj9DLfCU5qMvt7pump",
        },
        "YAITSIU": {
            "ticker": "YAIT",
            "contract_address": "5dDTxqg38NUY6ZKKGXXjaopWHt2xc3zSPoKhKmEEpump",
        },
        "LORE AI": {
            "ticker": "LORE",
            "contract_address": "G2AbNxcyXV6QiXptMm6MuQPBDJYp9AVQHTdWAV1Wpump",
        },
        "Cat Terminal": {
            "ticker": "CAT",
            "contract_address": "4HBQm2EhdpUWZkTYxttxNDnsoWi5beRAGWHpjVo8pump",
        },
        "TITAN AI": {
            "ticker": "TIAI",
            "contract_address": "He4FyrMqmDBP2yUk3UL4HLmgeUkcfhy1gcXuZPxtheBx",
        },
        "Real World AI": {
            "ticker": "RWA",
            "contract_address": "G8aVC4nk5oPWzTHp4PDm3kAuixCebv9WRQMD93h9pump",
        },
        "Fair and Free": {
            "ticker": "FAIR³",
            "contract_address": "42kgc4RDpWBMM5qtuaHenJuMzfk7nu1t7HSau74cpump",
        },
        "Homebrew Robotics Club": {
            "ticker": "BREW",
            "contract_address": "2hXQn7nJbh2XFTxvtyKb5mKfnScuoiC1Sm8rnWydpump",
        },
    }

    # Create reverse mapping from ticker to name for lookups
    TICKER_TO_NAME: ClassVar[Dict[str, str]] = {}

    def __init__(self):
        """Initialize the tool with the token mapping from ticker to name."""
        super().__init__()
        # Build reverse mapping from ticker to name
        for name, data in self.TOKEN_DATA.items():
            ticker = data["ticker"].upper()  # Normalize ticker to uppercase
            self.TICKER_TO_NAME[ticker] = name

    async def _arun(self, identifier: str) -> str:
        """Execute the token identification lookup asynchronously."""
        try:
            logger.info(f"[LUMOKIT] Token identification lookup for: {identifier}")

            # Clean up the identifier (remove $ if present, trim whitespace)
            identifier = identifier.strip()
            if identifier.startswith("$"):
                identifier = identifier[1:].strip()

            # Prepare results to collect matching tokens
            results = []

            # First try looking up by exact name match
            if identifier in self.TOKEN_DATA:
                token_data = self.TOKEN_DATA[identifier]
                results.append(
                    {
                        "name": identifier,
                        "ticker": token_data["ticker"],
                        "contract_address": token_data["contract_address"],
                    }
                )

            # Then try ticker lookup (case-insensitive)
            upper_identifier = identifier.upper()
            if upper_identifier in self.TICKER_TO_NAME:
                name = self.TICKER_TO_NAME[upper_identifier]
                token_data = self.TOKEN_DATA[name]

                # Only add if not already added by name lookup
                if not any(r["name"] == name for r in results):
                    results.append(
                        {
                            "name": name,
                            "ticker": token_data["ticker"],
                            "contract_address": token_data["contract_address"],
                        }
                    )

            # If no exact matches, search for partial matches in names and tickers
            if not results:
                for name, data in self.TOKEN_DATA.items():
                    # Check if the identifier is in the name (case-insensitive)
                    if identifier.lower() in name.lower():
                        results.append(
                            {
                                "name": name,
                                "ticker": data["ticker"],
                                "contract_address": data["contract_address"],
                            }
                        )
                        continue

                    # Check if the identifier is in the ticker (case-insensitive)
                    if identifier.lower() in data["ticker"].lower():
                        results.append(
                            {
                                "name": name,
                                "ticker": data["ticker"],
                                "contract_address": data["contract_address"],
                            }
                        )

            # Format the output
            if not results:
                return f"No token found matching '{identifier}'. Please verify the token name or ticker."

            if len(results) == 1:
                token = results[0]
                return f"Token: {token['name']} ({token['ticker']})\nContract Address: {token['contract_address']}"
            else:
                output = f"Found {len(results)} tokens matching '{identifier}':\n\n"
                for token in results:
                    output += f"• {token['name']} ({token['ticker']})\n  Contract Address: {token['contract_address']}\n\n"
                return output.strip()

        except Exception as e:
            logger.error(f"[LUMOKIT] Error in token identification tool: {str(e)}")
            return f"There was an error while looking up information for '{identifier}': {str(e)}"

    def _run(self, identifier: str) -> str:
        """Synchronous version not implemented."""
        raise NotImplementedError("This tool only supports async execution.")

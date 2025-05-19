from typing import ClassVar, Type

import aiohttp
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from settings.logger import logger

#################################################
#### COINGECKO GLOBAL CRYPTO DATA TOOL ####
#################################################


class CoinGeckoGlobalCryptoDataInput(BaseModel):
    """Input for the CoinGecko Global Crypto Data tool."""

    pass  # No input needed - just fetches global data


class CoinGeckoGlobalCryptoDataTool(BaseTool):
    """Tool for getting global cryptocurrency market data from CoinGecko."""

    name: ClassVar[str] = "coingecko_global_crypto_data_tool"
    description: ClassVar[str] = (
        "Get global cryptocurrency market data including market cap, volume, and dominance percentages."
    )
    args_schema: ClassVar[Type[BaseModel]] = CoinGeckoGlobalCryptoDataInput

    async def _arun(self) -> str:
        """Execute the CoinGecko global crypto data lookup asynchronously."""
        try:
            logger.info(f"[LUMOKIT] Fetching global crypto data from CoinGecko")

            # Construct the API URL for CoinGecko global data
            api_url = "https://api.coingecko.com/api/v3/global"

            # Make the API request
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        api_url, headers={"accept": "application/json"}
                    ) as response:
                        if response.status != 200:
                            logger.error(
                                f"[LUMOKIT] Error fetching CoinGecko global data: {response.status} - {await response.text()}"
                            )
                            return "I couldn't retrieve the global cryptocurrency market data at this time. The CoinGecko API might be experiencing issues or rate limiting."

                        data = await response.json()

                if "data" not in data:
                    logger.error(
                        f"[LUMOKIT] Unexpected response format from CoinGecko: {data}"
                    )
                    return "I couldn't process the cryptocurrency market data. The API response format was different than expected."

                # Extract the relevant data
                market_data = data["data"]

                # Format the response as a human-readable summary
                result = "## Global Cryptocurrency Market Overview\n\n"

                # Active cryptocurrencies and markets
                result += f"There are currently **{market_data['active_cryptocurrencies']:,}** active cryptocurrencies across **{market_data['markets']:,}** markets.\n\n"

                # Total market cap
                if (
                    "total_market_cap" in market_data
                    and "usd" in market_data["total_market_cap"]
                ):
                    total_market_cap_usd = market_data["total_market_cap"]["usd"]
                    result += f"**Total Market Cap**: ${total_market_cap_usd:,.2f} USD"

                    # Market cap change percentage
                    if "market_cap_change_percentage_24h_usd" in market_data:
                        change_pct = market_data["market_cap_change_percentage_24h_usd"]
                        change_sign = "+" if change_pct > 0 else ""
                        result += (
                            f" ({change_sign}{change_pct:.2f}% in the last 24h)\n\n"
                        )
                    else:
                        result += "\n\n"

            except Exception as e:
                logger.error(f"[LUMOKIT] Error processing CoinGecko data: {str(e)}")
                return "I couldn't retrieve the current cryptocurrency market data. Let me try a different approach to help you."

            # Trading volume
            if "total_volume" in market_data and "usd" in market_data["total_volume"]:
                total_volume_usd = market_data["total_volume"]["usd"]
                result += f"**24h Trading Volume**: ${total_volume_usd:,.2f} USD\n\n"

            # Market dominance
            if "market_cap_percentage" in market_data:
                result += "### Market Dominance\n"
                for coin, percentage in market_data["market_cap_percentage"].items():
                    result += f"- **{coin.upper()}**: {percentage:.2f}%\n"

            # Last updated time
            if "updated_at" in market_data:
                from datetime import datetime

                updated_time = datetime.fromtimestamp(market_data["updated_at"])
                result += f"\n*Data last updated: {updated_time.strftime('%Y-%m-%d %H:%M:%S')} UTC*"

            return result

        except Exception as e:
            logger.error(f"[LUMOKIT] Error in CoinGecko global data tool: {str(e)}")
            return f"I couldn't retrieve the global cryptocurrency market data at this time. There was an issue with the data source: {str(e)}"

    def _run(self) -> str:
        """Synchronous version not implemented."""
        try:
            raise NotImplementedError("This tool only supports async execution.")
        except Exception as e:
            logger.error(
                f"[LUMOKIT] Attempted to run synchronous version of CoinGecko tool: {str(e)}"
            )
            return "I can only access cryptocurrency market data asynchronously. Please try again."


#################################################
#### COINGECKO TRENDING TOOL ####
#################################################


class CoinGeckoTrendingInput(BaseModel):
    """Input for the CoinGecko Trending Tool."""

    pass  # No input needed - just fetches trending data


class CoinGeckoTrendingTool(BaseTool):
    """Tool for getting trending cryptocurrencies and NFTs from CoinGecko."""

    name: ClassVar[str] = "coingecko_trending_tool"
    description: ClassVar[str] = (
        "Get top trending coins and NFTs on CoinGecko based on user searches and trading volume."
    )
    args_schema: ClassVar[Type[BaseModel]] = CoinGeckoTrendingInput

    async def _arun(self) -> str:
        """Execute the CoinGecko trending data lookup asynchronously."""
        try:
            logger.info(f"[LUMOKIT] Fetching trending data from CoinGecko")

            # Construct the API URL for CoinGecko trending data
            api_url = "https://api.coingecko.com/api/v3/search/trending"

            # Make the API request
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        api_url, headers={"accept": "application/json"}
                    ) as response:
                        if response.status != 200:
                            logger.error(
                                f"[LUMOKIT] Error fetching CoinGecko trending data: {response.status} - {await response.text()}"
                            )
                            return "I couldn't retrieve the trending cryptocurrency data at this time. The CoinGecko API might be experiencing issues or rate limiting."

                        data = await response.json()

                if "coins" not in data or "nfts" not in data:
                    logger.error(
                        f"[LUMOKIT] Unexpected response format from CoinGecko: {data}"
                    )
                    return "I couldn't process the trending cryptocurrency data. The API response format was different than expected."

                # Format the response as a human-readable summary
                result = "## Trending Cryptocurrencies and NFTs on CoinGecko\n\n"

                # Process trending coins (top 7)
                result += "### Top Trending Coins (Last 24 Hours)\n"
                result += "These are the most searched coins by CoinGecko users in the last 24 hours:\n\n"

                for i, coin_data in enumerate(data["coins"][:7]):
                    coin = coin_data["item"]
                    price_btc = float(coin.get("price_btc", 0))
                    name = coin.get("name", "Unknown")
                    symbol = coin.get("symbol", "").upper()
                    market_cap_rank = coin.get("market_cap_rank", "N/A")

                    # Get 24h price change if available
                    price_change = "N/A"
                    if (
                        "data" in coin
                        and "price_change_percentage_24h" in coin["data"]
                        and "usd" in coin["data"]["price_change_percentage_24h"]
                    ):
                        change_pct = coin["data"]["price_change_percentage_24h"]["usd"]
                        change_sign = "+" if change_pct > 0 else ""
                        price_change = f"{change_sign}{change_pct:.2f}%"

                    # Format market cap if available
                    market_cap = "N/A"
                    if "data" in coin and "market_cap" in coin["data"]:
                        market_cap = coin["data"]["market_cap"]

                    result += (
                        f"**{i + 1}. {name} ({symbol})** - Rank #{market_cap_rank}\n"
                    )
                    result += f"   • Price: {price_btc:.8f} BTC\n"
                    result += f"   • 24h Change: {price_change}\n"
                    result += f"   • Market Cap: {market_cap}\n\n"

                # Process trending NFTs (top 5)
                if data["nfts"] and len(data["nfts"]) > 0:
                    result += "### Top Trending NFTs (By Trading Volume)\n"
                    result += "These NFT collections have the highest trading volume in the last 24 hours:\n\n"

                    for i, nft in enumerate(data["nfts"][:5]):
                        name = nft.get("name", "Unknown")
                        symbol = nft.get("symbol", "").upper()
                        native_currency = nft.get(
                            "native_currency_symbol", "eth"
                        ).upper()
                        floor_price = nft.get("floor_price_in_native_currency", 0)

                        # Get 24h price change if available
                        price_change = "N/A"
                        if "floor_price_24h_percentage_change" in nft:
                            change_pct = nft["floor_price_24h_percentage_change"]
                            change_sign = "+" if change_pct > 0 else ""
                            price_change = f"{change_sign}{change_pct:.2f}%"

                        # Get 24h volume if available
                        volume = "N/A"
                        if "data" in nft and "h24_volume" in nft["data"]:
                            volume = nft["data"]["h24_volume"]

                        result += f"**{i + 1}. {name} ({symbol})**\n"
                        result += (
                            f"   • Floor Price: {floor_price:.4f} {native_currency}\n"
                        )
                        result += f"   • 24h Change: {price_change}\n"
                        result += f"   • 24h Volume: {volume}\n\n"

                return result

            except Exception as e:
                logger.error(
                    f"[LUMOKIT] Error processing CoinGecko trending data: {str(e)}"
                )
                return "I couldn't retrieve the current trending cryptocurrency data. Let me try a different approach to help you."

        except Exception as e:
            logger.error(f"[LUMOKIT] Error in CoinGecko trending tool: {str(e)}")
            return f"I couldn't retrieve the trending cryptocurrency data at this time. There was an issue with the data source: {str(e)}"

    def _run(self) -> str:
        """Synchronous version not implemented."""
        try:
            raise NotImplementedError("This tool only supports async execution.")
        except Exception as e:
            logger.error(
                f"[LUMOKIT] Attempted to run synchronous version of CoinGecko trending tool: {str(e)}"
            )
            return "I can only access trending cryptocurrency data asynchronously. Please try again."


#################################################
#### COINGECKO EXCHANGE RATES TOOL ####
#################################################


class CoinGeckoExchangeRatesInput(BaseModel):
    """Input for the CoinGecko Exchange Rates Tool."""

    pass  # No input needed - just fetches exchange rate data


class CoinGeckoExchangeRatesTool(BaseTool):
    """Tool for getting BTC-to-Currency exchange rates from CoinGecko."""

    name: ClassVar[str] = "coingecko_exchange_rates_tool"
    description: ClassVar[str] = (
        "Get Bitcoin-to-currency exchange rates for major cryptocurrencies, fiat currencies, and commodities."
    )
    args_schema: ClassVar[Type[BaseModel]] = CoinGeckoExchangeRatesInput

    async def _arun(self) -> str:
        """Execute the CoinGecko exchange rates lookup asynchronously."""
        try:
            logger.info(f"[LUMOKIT] Fetching exchange rates data from CoinGecko")

            # Construct the API URL for CoinGecko exchange rates
            api_url = "https://api.coingecko.com/api/v3/exchange_rates"

            # Make the API request
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        api_url, headers={"accept": "application/json"}
                    ) as response:
                        if response.status != 200:
                            logger.error(
                                f"[LUMOKIT] Error fetching CoinGecko exchange rates: {response.status} - {await response.text()}"
                            )
                            return "I couldn't retrieve the exchange rates data at this time. The CoinGecko API might be experiencing issues or rate limiting."

                        data = await response.json()

                if "rates" not in data:
                    logger.error(
                        f"[LUMOKIT] Unexpected response format from CoinGecko: {data}"
                    )
                    return "I couldn't process the exchange rates data. The API response format was different than expected."

                # Format the response as a human-readable summary
                result = "## Bitcoin Exchange Rates\n\n"
                result += "Here are the current exchange rates for 1 Bitcoin (BTC):\n\n"

                # Categorize rates by type
                crypto_rates = {}
                fiat_rates = {}
                commodity_rates = {}

                for code, rate_data in data["rates"].items():
                    # Skip BTC itself (value will be 1)
                    if code == "btc":
                        continue

                    rate_type = rate_data.get("type", "")
                    name = rate_data.get("name", "")
                    unit = rate_data.get("unit", "")
                    value = rate_data.get("value", 0)

                    # Add to appropriate category
                    rate_info = {"name": name, "unit": unit, "value": value}
                    if rate_type == "crypto":
                        crypto_rates[code] = rate_info
                    elif rate_type == "fiat":
                        fiat_rates[code] = rate_info
                    elif rate_type == "commodity":
                        commodity_rates[code] = rate_info

                # Add major cryptocurrencies
                result += "### Major Cryptocurrencies\n"
                major_cryptos = ["eth", "bnb", "xrp", "sol", "ada", "doge"]
                for code in major_cryptos:
                    if code in crypto_rates:
                        rate = crypto_rates[code]
                        result += f"- **{rate['name']} ({code.upper()})**: {rate['value']:,.2f} {rate['unit']}\n"
                result += "\n"

                # Add major fiat currencies
                result += "### Major Fiat Currencies\n"
                major_fiats = ["usd", "eur", "gbp", "jpy", "cny", "cad", "aud", "inr"]
                for code in major_fiats:
                    if code in fiat_rates:
                        rate = fiat_rates[code]
                        result += f"- **{rate['name']} ({code.upper()})**: {rate['value']:,.2f} {rate['unit']}\n"
                result += "\n"

                # Add commodities
                result += "### Commodities\n"
                for code, rate in commodity_rates.items():
                    result += (
                        f"- **{rate['name']}**: {rate['value']:,.3f} {rate['unit']}\n"
                    )
                result += "\n"

                result += "*These rates represent how many units of each currency or commodity you can get for 1 Bitcoin.*"
                result += "\n\n*Data provided by CoinGecko*"

                return result

            except Exception as e:
                logger.error(
                    f"[LUMOKIT] Error processing CoinGecko exchange rates data: {str(e)}"
                )
                return "I couldn't retrieve the current exchange rates data. Let me try a different approach to help you."

        except Exception as e:
            logger.error(f"[LUMOKIT] Error in CoinGecko exchange rates tool: {str(e)}")
            return f"I couldn't retrieve the exchange rates data at this time. There was an issue with the data source: {str(e)}"

    def _run(self) -> str:
        """Synchronous version not implemented."""
        try:
            raise NotImplementedError("This tool only supports async execution.")
        except Exception as e:
            logger.error(
                f"[LUMOKIT] Attempted to run synchronous version of CoinGecko exchange rates tool: {str(e)}"
            )
            return "I can only access exchange rates data asynchronously. Please try again."


#################################################
#### COINGECKO COIN DATA TOOL ####
#################################################


class CoinGeckoCoinDataInput(BaseModel):
    """Input for the CoinGecko Coin Data Tool."""

    coinname: str = Field(
        ...,
        description="The name of the cryptocurrency (e.g., bitcoin, ethereum, solana) or multiple cryptocurrencies separated by commas (e.g., 'bitcoin,ethereum,solana').",
    )


class CoinGeckoCoinDataTool(BaseTool):
    """Tool for getting detailed market data for a specific cryptocurrency from CoinGecko."""

    name: ClassVar[str] = "coingecko_coin_data_tool"
    description: ClassVar[str] = (
        "Get detailed market data (price, volume, market cap) for specific cryptocurrencies. Provide one coin name like 'bitcoin' or multiple coins separated by commas like 'bitcoin,ethereum,solana'."
    )
    args_schema: ClassVar[Type[BaseModel]] = CoinGeckoCoinDataInput

    async def _arun(self, coinname: str) -> str:
        """Execute the CoinGecko coin data lookup asynchronously."""
        try:
            # Check if multiple coins are provided (comma-separated)
            coin_names = [name.strip() for name in coinname.split(",")]
            logger.info(f"[LUMOKIT] Fetching coin data from CoinGecko for {coin_names}")

            # Comprehensive coin name and symbol mappings to CoinGecko IDs
            coin_mappings = {
                # Major cryptocurrencies
                "btc": "bitcoin",
                "bitcoin": "bitcoin",
                "eth": "ethereum",
                "ethereum": "ethereum",
                "sol": "solana",
                "solana": "solana",
                "doge": "dogecoin",
                "dogecoin": "dogecoin",
                "shib": "shiba-inu",
                "shiba": "shiba-inu",
                "shiba inu": "shiba-inu",
                "xrp": "ripple",
                "ripple": "ripple",
                "dot": "polkadot",
                "polkadot": "polkadot",
                "avax": "avalanche-2",
                "avalanche": "avalanche-2",
                "ada": "cardano",
                "cardano": "cardano",
                "matic": "polygon",
                "polygon": "polygon",
                "link": "chainlink",
                "chainlink": "chainlink",
                "uni": "uniswap",
                "uniswap": "uniswap",
                "bnb": "binancecoin",
                "binance coin": "binancecoin",
                "binancecoin": "binancecoin",
                "wbtc": "wrapped-bitcoin",
                "wrapped bitcoin": "wrapped-bitcoin",
                # Stablecoins
                "usdt": "tether",
                "tether": "tether",
                "usdc": "usd-coin",
                "usd coin": "usd-coin",
                "dai": "dai",
                "busd": "binance-usd",
                "binance usd": "binance-usd",
                "tusd": "true-usd",
                "true usd": "true-usd",
                "usdd": "usdd",
                "frax": "frax",
                # Layer 1 blockchains
                "trx": "tron",
                "tron": "tron",
                "near": "near",
                "near protocol": "near",
                "ftm": "fantom",
                "fantom": "fantom",
                "atom": "cosmos",
                "cosmos": "cosmos",
                "algo": "algorand",
                "algorand": "algorand",
                "hbar": "hedera-hashgraph",
                "hedera": "hedera-hashgraph",
                "hedera hashgraph": "hedera-hashgraph",
                "egld": "elrond-erd-2",
                "elrond": "elrond-erd-2",
                "multiversx": "elrond-erd-2",
                "one": "harmony",
                "harmony": "harmony",
                "kaspa": "kaspa",
                "kda": "kadena",
                "kadena": "kadena",
                "zil": "zilliqa",
                "zilliqa": "zilliqa",
                # DeFi
                "aave": "aave",
                "comp": "compound-governance-token",
                "compound": "compound-governance-token",
                "cake": "pancakeswap-token",
                "pancakeswap": "pancakeswap-token",
                "sushi": "sushi",
                "sushiswap": "sushi",
                "crv": "curve-dao-token",
                "curve": "curve-dao-token",
                "mkr": "maker",
                "maker": "maker",
                "snx": "havven",
                "synthetix": "havven",
                "yfi": "yearn-finance",
                "yearn": "yearn-finance",
                "yearn finance": "yearn-finance",
                "ldo": "lido-dao",
                "lido": "lido-dao",
                "lido dao": "lido-dao",
                "gmx": "gmx",
                "bal": "balancer",
                "balancer": "balancer",
                "ren": "republic-protocol",
                "1inch": "1inch",
                # Exchange tokens
                "okb": "okb",
                "kcs": "kucoin-shares",
                "kucoin": "kucoin-shares",
                "ftt": "ftx-token",
                "ftx": "ftx-token",
                "leo": "leo-token",
                "bitfinex": "leo-token",
                "cro": "crypto-com-chain",
                "cronos": "crypto-com-chain",
                "crypto.com": "crypto-com-chain",
                "ht": "huobi-token",
                "huobi": "huobi-token",
                # Memecoins and community tokens
                "pepe": "pepe",
                "bonk": "bonk",
                "floki": "floki",
                "floki inu": "floki",
                "babydoge": "baby-doge-coin",
                "baby doge": "baby-doge-coin",
                "elon": "dogelon-mars",
                "dogelon": "dogelon-mars",
                "dogelon mars": "dogelon-mars",
                "samo": "samoyedcoin",
                "samoyedcoin": "samoyedcoin",
                "mog": "mogcoin",
                "book": "book-token",
                "popcat": "popcat",
                "wif": "dogwifhat",
                "dogwifhat": "dogwifhat",
                "cat": "cat-token",
                "moon": "mooncoin",
                "rats": "rats-token",
                # Gaming & Metaverse
                "sand": "the-sandbox",
                "sandbox": "the-sandbox",
                "mana": "decentraland",
                "decentraland": "decentraland",
                "axs": "axie-infinity",
                "axie": "axie-infinity",
                "axie infinity": "axie-infinity",
                "enjin": "enjincoin",
                "enj": "enjincoin",
                "gala": "gala",
                "imx": "immutable-x",
                "immutable": "immutable-x",
                "immutable x": "immutable-x",
                "ilv": "illuvium",
                "illuvium": "illuvium",
                "flow": "flow",
                # Privacy coins
                "xmr": "monero",
                "monero": "monero",
                "zec": "zcash",
                "zcash": "zcash",
                "dash": "dash",
                # Other notable projects
                "arb": "arbitrum",
                "arbitrum": "arbitrum",
                "op": "optimism",
                "optimism": "optimism",
                "ape": "apecoin",
                "apecoin": "apecoin",
                "chz": "chiliz",
                "chiliz": "chiliz",
                "lrc": "loopring",
                "loopring": "loopring",
                "rune": "thorchain",
                "thorchain": "thorchain",
                "theta": "theta-token",
                "fet": "fetch-ai",
                "fetch": "fetch-ai",
                "fetch ai": "fetch-ai",
                "qnt": "quant-network",
                "quant": "quant-network",
                "gt": "gatechain-token",
                "gatechain": "gatechain-token",
                "vet": "vechain",
                "vechain": "vechain",
                "icp": "internet-computer",
                "internet computer": "internet-computer",
                "ar": "arweave",
                "arweave": "arweave",
                "bat": "basic-attention-token",
                "basic attention token": "basic-attention-token",
                "grt": "the-graph",
                "graph": "the-graph",
                "the graph": "the-graph",
                "sc": "siacoin",
                "siacoin": "siacoin",
                "stx": "blockstack",
                "stacks": "blockstack",
                "blockstack": "blockstack",
                "bch": "bitcoin-cash",
                "bitcoin cash": "bitcoin-cash",
                "ltc": "litecoin",
                "litecoin": "litecoin",
                "xlm": "stellar",
                "stellar": "stellar",
                "etc": "ethereum-classic",
                "ethereum classic": "ethereum-classic",
                "fil": "filecoin",
                "filecoin": "filecoin",
                "xtz": "tezos",
                "tezos": "tezos",
                "neo": "neo",
                "miota": "iota",
                "iota": "iota",
                "hot": "holotoken",
                "holo": "holotoken",
                "dcr": "decred",
                "decred": "decred",
                "waves": "waves",
                "xem": "nem",
                "nem": "nem",
                "eos": "eos",
                "zrx": "0x",
                "0x": "0x",
                "inch": "1inch",
                "reef": "reef-finance",
                "reef finance": "reef-finance",
                "dydx": "dydx",
                "mask": "mask-network",
                "mask network": "mask-network",
                "audio": "audius",
                "audius": "audius",
                "rvn": "ravencoin",
                "ravencoin": "ravencoin",
                "omi": "ecomi",
                "ecomi": "ecomi",
                # Newer/trending coins
                "sei": "sei-network",
                "sei network": "sei-network",
                "sui": "sui",
                "blur": "blur",
                "tia": "celestia",
                "celestia": "celestia",
                "inj": "injective-protocol",
                "injective": "injective-protocol",
                "pyth": "pyth-network",
                "pyth network": "pyth-network",
                "jto": "jito",
                "jito": "jito",
                "bome": "book-of-meme",
                "book of meme": "book-of-meme",
                "ondo": "ondo-finance",
                "ondo finance": "ondo-finance",
                "render": "render-token",
                "rndr": "render-token",
            }

            # Process each coin name to get the corresponding CoinGecko ID
            coin_ids = []
            for name in coin_names:
                coin_id = name.lower().strip().replace(" ", "-")
                if coin_id in coin_mappings:
                    coin_ids.append(coin_mappings[coin_id])
                else:
                    coin_ids.append(coin_id)

            # Join the IDs for the API request
            ids_param = ",".join(coin_ids)

            # Construct the API URL for CoinGecko coin data with multiple IDs
            api_url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids={ids_param}&order=market_cap_desc&per_page={len(coin_ids)}&page=1&sparkline=false&locale=en"

            # Make the API request
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        api_url, headers={"accept": "application/json"}
                    ) as response:
                        if response.status != 200:
                            logger.error(
                                f"[LUMOKIT] Error fetching CoinGecko data for {ids_param}: {response.status} - {await response.text()}"
                            )
                            return f"I couldn't retrieve the market data for the requested cryptocurrencies at this time. The CoinGecko API might be experiencing issues, or one of the coin names might be incorrect."

                        data = await response.json()

                if not data or len(data) == 0:
                    logger.error(
                        f"[LUMOKIT] No data returned from CoinGecko for {ids_param}"
                    )
                    return f"I couldn't find any data for the cryptocurrencies you requested. Please verify the coin names and try again. For example, use 'bitcoin', 'ethereum', or 'solana'."

                # Format the response as a human-readable summary
                result = "## Cryptocurrency Market Data\n\n"

                # Process each coin in the response
                for coin_data in data:
                    result += (
                        f"### {coin_data['name']} ({coin_data['symbol'].upper()})\n\n"
                    )

                    # Current price and market cap
                    result += (
                        f"**Current Price**: ${coin_data['current_price']:,.2f} USD\n"
                    )
                    result += f"**Market Cap**: ${coin_data['market_cap']:,.0f} USD (Rank #{coin_data['market_cap_rank']})\n"

                    # 24h trading information
                    result += f"**24h Trading Volume**: ${coin_data['total_volume']:,.0f} USD\n"
                    result += f"**24h Price Range**: ${coin_data['low_24h']:,.2f} - ${coin_data['high_24h']:,.2f} USD\n"

                    # Price change information
                    price_change = coin_data.get("price_change_24h", 0)
                    price_change_pct = coin_data.get("price_change_percentage_24h", 0)
                    price_change_sign = "+" if price_change >= 0 else ""
                    result += f"**24h Price Change**: {price_change_sign}${price_change:.2f} USD ({price_change_sign}{price_change_pct:.2f}%)\n\n"

                    # Add a separator between coins (except for the last one)
                    if coin_data != data[-1]:
                        result += "---\n\n"

                # Last updated
                if data and "last_updated" in data[0]:
                    last_updated = (
                        data[0]["last_updated"].replace("Z", " UTC").replace("T", " ")
                    )
                    result += f"*Data last updated: {last_updated}*"

                return result

            except Exception as e:
                logger.error(
                    f"[LUMOKIT] Error processing CoinGecko coin data: {str(e)}"
                )
                return f"I couldn't retrieve the market data for the requested cryptocurrencies. Let me try a different approach to help you."

        except Exception as e:
            logger.error(f"[LUMOKIT] Error in CoinGecko coin data tool: {str(e)}")
            return f"I couldn't retrieve the market data for the requested cryptocurrencies at this time. There was an issue with the data source: {str(e)}"

    def _run(self, coinname: str) -> str:
        """Synchronous version not implemented."""
        try:
            raise NotImplementedError("This tool only supports async execution.")
        except Exception as e:
            logger.error(
                f"[LUMOKIT] Attempted to run synchronous version of CoinGecko coin data tool: {str(e)}"
            )
            return "I can only access cryptocurrency market data asynchronously. Please try again."

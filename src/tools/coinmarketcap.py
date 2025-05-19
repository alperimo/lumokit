import asyncio
from datetime import datetime
from typing import ClassVar, Type

import requests
from bs4 import BeautifulSoup
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from settings.config import CONFIG
from settings.logger import logger

#################################################
#### CMC CRYPTO NEWS TOOL ####
#################################################


class CMCCryptoNewsInput(BaseModel):
    """Input for the CMC Crypto News tool."""

    limit: int = Field(
        default=8, description="Number of news articles to fetch (max 8)"
    )


class CMCCryptoNewsTool(BaseTool):
    """Tool for getting the latest crypto news from CoinMarketCap."""

    name: ClassVar[str] = "cmc_crypto_news_tool"
    description: ClassVar[str] = "Get the latest crypto news from CoinMarketCap."
    args_schema: ClassVar[Type[BaseModel]] = CMCCryptoNewsInput

    async def _arun(self, limit: int = 8) -> str:
        """Execute the CMC crypto news lookup asynchronously."""
        try:
            logger.info(f"[LUMOKIT] Fetching latest {limit} crypto news from CMC")

            # Validate the limit
            if limit <= 0:
                limit = 8
            elif limit > 8:
                limit = 8

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            }

            # Make the request
            response = requests.get(
                "https://coinmarketcap.com/headlines/news/", headers=headers, timeout=10
            )
            response.raise_for_status()

            # Parse the HTML
            soup = BeautifulSoup(response.content, "html.parser")
            news_items = soup.find_all("div", class_="lkurXo")

            if not news_items:
                return "No crypto news available at this time."

            news_data = []
            current_time = datetime.now()

            # Extract news data
            for item in news_items:
                try:
                    heading = item.find("a", class_="kNLySu").text.strip()
                    body = item.find("p", class_="iTULwH").text.strip()

                    tickers = []
                    ticker_elements = item.find_all("span", class_="eydMEP")
                    for ticker in ticker_elements:
                        tickers.append(ticker.text.strip())

                    time_str = item.find("p", class_="fdCzQf").text.strip()
                    posted_hour, posted_min = map(int, time_str.split(":"))
                    posted_time = datetime.now().replace(
                        hour=posted_hour, minute=posted_min
                    )

                    if posted_time > current_time:
                        posted_time = posted_time.replace(day=posted_time.day - 1)

                    time_diff = int((current_time - posted_time).total_seconds() / 60)

                    news_data.append(
                        {
                            "heading": heading,
                            "body": body,
                            "tickers": tickers,
                            "minutes_ago": time_diff,
                        }
                    )

                except (AttributeError, IndexError) as e:
                    logger.error(f"[LUMOKIT] Error extracting news item: {e}")
                    continue

            # Format the output
            formatted_output = [
                f"The latest {min(limit, len(news_data))} crypto news articles are as follows:"
            ]

            for i, news_item in enumerate(news_data[:limit]):
                ticker_str = (
                    ", ".join(f"${ticker}" for ticker in news_item["tickers"])
                    if news_item["tickers"]
                    else "no specific tickers"
                )
                output = (
                    f"Article {i + 1}: '{news_item['heading']}'\n"
                    f"Content: '{news_item['body']}'\n"
                    f"Tickers: {ticker_str}\n"
                    f"Posted: {news_item['minutes_ago']} minutes ago"
                )
                formatted_output.append(output)
                if i < min(limit, len(news_data)) - 1:
                    formatted_output.append("----------")

            return "\n".join(formatted_output)

        except Exception as e:
            logger.error(f"[LUMOKIT] Error in CMC crypto news tool: {str(e)}")
            return "I couldn't retrieve the latest crypto news at this moment. This could be due to connectivity issues or changes to the CoinMarketCap website. Please try again later or check directly on CoinMarketCap."

    def _run(self, limit: int = 8) -> str:
        """Synchronous version not implemented."""
        raise NotImplementedError("This tool only supports async execution.")


#################################################
#### CMC TRENDING COINS TOOL ####
#################################################


class CMCTrendingCoinsInput(BaseModel):
    """Input for the CMC Trending Coins tool."""

    limit: int = Field(
        default=20, description="Number of trending coins to fetch (max 100)"
    )


class CMCTrendingCoinsTool(BaseTool):
    """Tool for getting the latest trending coins from CoinMarketCap."""

    name: ClassVar[str] = "cmc_trending_coins_tool"
    description: ClassVar[str] = (
        "Get a list of all active cryptocurrencies with latest market data from CoinMarketCap."
    )
    args_schema: ClassVar[Type[BaseModel]] = CMCTrendingCoinsInput

    async def _arun(self, limit: int = 20) -> str:
        """Execute the CMC trending coins lookup asynchronously."""
        try:
            logger.info(f"[LUMOKIT] Fetching latest {limit} trending coins from CMC")

            # Validate the limit
            if limit <= 0:
                limit = 20
            elif limit > 100:
                limit = 100

            # API URL
            base_url = "https://pro-api.coinmarketcap.com/"
            endpoint = "v1/cryptocurrency/listings/latest"
            url = base_url + endpoint

            # Set up the parameters
            parameters = {"limit": limit, "convert": "USD"}

            # Set up headers with API key
            headers = {
                "Accepts": "application/json",
                "X-CMC_PRO_API_KEY": CONFIG.CMC_API_KEY,
            }

            # Log API call information (without exposing the key)
            logger.info(f"[LUMOKIT] Calling CMC API: {url} with params: {parameters}")

            # Create session and set headers
            session = requests.Session()
            session.headers.update(headers)

            # Make the request with error handling
            try:
                response = session.get(url, params=parameters, timeout=10)
                response.raise_for_status()  # Raise an exception for HTTP errors

                # Parse JSON response
                data = response.json()

                if not data.get("data"):
                    return "No trending coins data available at this time."

                coin_data = data.get("data", [])

                # Format the output as a summarized list
                formatted_output = [
                    f"Here are the top {len(coin_data)} cryptocurrencies by market cap:"
                ]

                for i, coin in enumerate(coin_data):
                    name = coin.get("name", "Unknown")
                    symbol = coin.get("symbol", "Unknown")
                    rank = coin.get("cmc_rank", "N/A")

                    quote = coin.get("quote", {}).get("USD", {})
                    price = quote.get("price", 0)
                    market_cap = quote.get("market_cap", 0)
                    percent_change_24h = quote.get("percent_change_24h", 0)

                    price_formatted = f"${price:.2f}" if price < 1 else f"${price:,.2f}"
                    market_cap_formatted = f"${market_cap:,.0f}"
                    percent_change_formatted = f"{percent_change_24h:.2f}%"
                    change_indicator = "📈" if percent_change_24h >= 0 else "📉"

                    output = (
                        f"{rank}. {name} ({symbol}): {price_formatted} | "
                        f"Market Cap: {market_cap_formatted} | "
                        f"24h Change: {change_indicator} {percent_change_formatted}"
                    )

                    formatted_output.append(output)

                return "\n\n".join(formatted_output)

            except requests.exceptions.HTTPError as e:
                # Handle HTTP errors (like 401 Unauthorized)
                logger.error(f"[LUMOKIT] HTTP Error in CMC trending coins tool: {e}")
                status_code = (
                    e.response.status_code if hasattr(e, "response") else "unknown"
                )
                if status_code == 401:
                    return "Failed to authenticate with CoinMarketCap API. Please check your API key."
                elif status_code == 429:
                    return "Rate limit exceeded for CoinMarketCap API. Please try again later."
                else:
                    return f"HTTP Error from CoinMarketCap API: {status_code}"

            except requests.exceptions.ConnectionError:
                logger.error("[LUMOKIT] Connection error with CMC API")
                return "Failed to connect to CoinMarketCap API. Please check your internet connection."

            except requests.exceptions.Timeout:
                logger.error("[LUMOKIT] Timeout error with CMC API")
                return "Request to CoinMarketCap API timed out. Please try again later."

            except requests.exceptions.RequestException as e:
                logger.error(f"[LUMOKIT] Request error with CMC API: {e}")
                return "Error making request to CoinMarketCap API."

        except Exception as e:
            logger.error(f"[LUMOKIT] Error in CMC trending coins tool: {str(e)}")
            logger.error(traceback.format_exc())
            return "I couldn't retrieve the latest trending coins at this moment. This could be due to API limits, connectivity issues, or an invalid API key configuration."

    def _run(self, limit: int = 20) -> str:
        """Synchronous version not implemented."""
        raise NotImplementedError("This tool only supports async execution.")

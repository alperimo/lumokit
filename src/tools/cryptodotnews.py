import asyncio
from typing import ClassVar, Type

import requests
from bs4 import BeautifulSoup
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from settings.logger import logger

#################################################
#### CRYPTO.NEWS MEMECOINS NEWS TOOL ####
#################################################


class CNMemecoinsNewsInput(BaseModel):
    """Input for the Crypto.news Memecoins News tool."""

    limit: int = Field(
        default=8, description="Number of memecoin news articles to fetch (max 8)"
    )


class CNMemecoinsNewsTool(BaseTool):
    """Tool for getting the latest memecoin news from Crypto.news."""

    name: ClassVar[str] = "cn_memecoins_news_tool"
    description: ClassVar[str] = "Get the latest memecoin news from Crypto.news."
    args_schema: ClassVar[Type[BaseModel]] = CNMemecoinsNewsInput

    async def _arun(self, limit: int = 8) -> str:
        """Execute the Crypto.news memecoins news lookup asynchronously."""
        try:
            logger.info(
                f"[LUMOKIT] Fetching latest {limit} memecoin news from Crypto.news"
            )

            # Validate the limit
            if limit <= 0:
                limit = 8
            elif limit > 8:
                limit = 8

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }

            # Make the request
            response = requests.get(
                "https://crypto.news/tag/meme-coin/", headers=headers, timeout=10
            )
            response.raise_for_status()

            # Parse the HTML
            soup = BeautifulSoup(response.content, "html.parser")
            news_items = soup.find_all("div", class_="post-loop--style-horizontal")

            if not news_items:
                return "No memecoin news available at this time."

            news_data = []

            # Extract news data
            for item in news_items:
                try:
                    heading = item.find("p", class_="post-loop__title").text.strip()
                    body = item.find("div", class_="post-loop__summary").text.strip()

                    tickers = []
                    ticker_elements = item.find_all(
                        "span", class_="token-badge__symbol"
                    )
                    for ticker in ticker_elements:
                        tickers.append(ticker.text.strip())

                    time_posted = item.find(
                        "time", class_="post-loop__date"
                    ).text.strip()

                    news_data.append(
                        {
                            "heading": heading,
                            "body": body,
                            "tickers": tickers,
                            "time_posted": time_posted,
                        }
                    )

                except (AttributeError, IndexError) as e:
                    logger.error(f"[LUMOKIT] Error extracting memecoin news item: {e}")
                    continue

            # Format the output
            formatted_output = [
                f"The latest {min(limit, len(news_data))} memecoin news articles are as follows:"
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
                    f"Posted: {news_item['time_posted']}"
                )
                formatted_output.append(output)
                if i < min(limit, len(news_data)) - 1:
                    formatted_output.append("----------")

            return "\n".join(formatted_output)

        except Exception as e:
            logger.error(f"[LUMOKIT] Error in Crypto.news memecoin news tool: {str(e)}")
            return "I couldn't retrieve the latest memecoin news at this moment. This could be due to connectivity issues or changes in the website structure. Please try again later."

    def _run(self, limit: int = 8) -> str:
        """Synchronous version not implemented."""
        raise NotImplementedError("This tool only supports async execution.")

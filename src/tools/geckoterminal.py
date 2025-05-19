import asyncio
from typing import ClassVar, Type

import aiohttp
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from settings.logger import logger

#################################################
#### GECKOTERMINAL TRENDING PUMP.FUN TOKENS TOOL ####
#################################################


class GTPumpFunTrendingInput(BaseModel):
    """Input for the GeckoTerminal Trending Pump.fun Tokens tool."""

    limit: int = Field(
        default=10, description="Number of trending tokens to fetch (max 10)"
    )


class GTPumpFunTrendingTool(BaseTool):
    """Tool for getting the latest trending Pump.fun tokens from GeckoTerminal."""

    name: ClassVar[str] = "geckoterminal_trending_pumpfun_tool"
    description: ClassVar[str] = (
        "Get the latest trending tokens from the Pump.fun category on GeckoTerminal."
    )
    args_schema: ClassVar[Type[BaseModel]] = GTPumpFunTrendingInput

    @staticmethod
    def parse_numeric_value(value, default="0"):
        """Parse numeric values, handling special cases."""
        if value is None:
            return default
        try:
            return f"{float(value):.2f}" if value else default
        except (ValueError, TypeError):
            return default

    async def _arun(self, limit: int = 10) -> str:
        """Execute the GeckoTerminal Pump.fun trending tokens lookup asynchronously."""
        try:
            logger.info(
                "[LUMOKIT] Fetching latest trending Pump.fun tokens from GeckoTerminal API"
            )

            # Fixed to always fetch 10 items
            limit = 10

            # API endpoint for PumpSwap pools sorted by 24h volume
            api_url = "https://api.geckoterminal.com/api/v2/networks/solana/dexes/pumpswap/pools"
            params = {"page": 1, "sort": "h24_volume_usd_desc"}

            # Make the API request
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, params=params) as response:
                    if response.status != 200:
                        logger.error(
                            f"[LUMOKIT] Error fetching GeckoTerminal API data: {response.status}"
                        )
                        return "Could not fetch trending Pump.fun tokens at this time."

                    data = await response.json()

            # Check if we have pools data
            if not data or "data" not in data or not data["data"]:
                return "No trending Pump.fun tokens available at this time."

            # Take only the top 10 tokens
            pools = data["data"][:limit]

            formatted_output = [
                "# Latest Trending Pump.fun Tokens\n"
                "Here are the top trending tokens from the Pump.fun category:"
            ]

            # Extract and format token data
            for i, pool in enumerate(pools):
                try:
                    attributes = pool["attributes"]
                    name = attributes["name"]
                    base_token_price_usd = self.parse_numeric_value(
                        attributes["base_token_price_usd"]
                    )

                    # Extract price change percentages
                    price_changes = attributes.get("price_change_percentage", {})
                    price_change_5m = f"{price_changes.get('m5', '0')}%"
                    price_change_1h = f"{price_changes.get('h1', '0')}%"
                    price_change_6h = f"{price_changes.get('h6', '0')}%"
                    price_change_24h = f"{price_changes.get('h24', '0')}%"

                    # Extract volume data
                    volume_data = attributes.get("volume_usd", {})
                    volume_24h = self.parse_numeric_value(volume_data.get("h24", 0))

                    # Get market cap and liquidity data
                    fdv = self.parse_numeric_value(attributes.get("fdv_usd", 0))
                    liquidity = self.parse_numeric_value(
                        attributes.get("reserve_in_usd", 0)
                    )

                    # Format the output for this token
                    token_parts = name.split(" / ")
                    token_name = token_parts[0] if len(token_parts) > 0 else name
                    token_pair = token_parts[1] if len(token_parts) > 1 else "SOL"

                    output_text = (
                        f"## {i + 1}. {token_name} (${token_pair})\n"
                        f"- **Current Price**: ${base_token_price_usd}\n"
                        f"- **Price Changes**:\n"
                        f"  - 5 minutes: {price_change_5m}\n"
                        f"  - 1 hour: {price_change_1h}\n"
                        f"  - 6 hours: {price_change_6h}\n"
                        f"  - 24 hours: {price_change_24h}\n"
                        f"- **24h Volume**: ${volume_24h}\n"
                        f"- **Liquidity**: ${liquidity}\n"
                        f"- **Fully Diluted Valuation**: ${fdv}"
                    )

                    formatted_output.append(output_text)

                    # Add a separator between tokens
                    if i < len(pools) - 1:
                        formatted_output.append("---")

                except (KeyError, TypeError) as e:
                    logger.error(
                        f"[LUMOKIT] Error extracting Pump.fun token data: {str(e)}"
                    )
                    continue

            return "\n".join(formatted_output)

        except Exception as e:
            logger.error(
                f"[LUMOKIT] Error in GeckoTerminal Pump.fun trending tokens tool: {str(e)}"
            )
            return "I couldn't fetch trending Pump.fun tokens data at this time."

    def _run(self, limit: int = 10) -> str:
        """Synchronous version not implemented."""
        return "This tool only supports asynchronous execution. Please use the async version instead."

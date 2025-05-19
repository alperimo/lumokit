from typing import ClassVar, Type

import aiohttp
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from settings.config import CONFIG
from settings.logger import logger

#################################################
#### BIRDEYE TOKEN TRENDING TOOL ####
#################################################


class BirdeyeTokenTrendingInput(BaseModel):
    """Input for the BirdEye token trending tool."""

    limit: int = Field(
        default=10, description="Number of trending tokens to retrieve (max 20)"
    )


class BirdeyeTokenTrendingTool(BaseTool):
    """Tool for getting the top trending tokens on Solana from BirdEye."""

    name: ClassVar[str] = "birdeye_token_trending_tool"
    description: ClassVar[str] = (
        "Get a list of top trending tokens on Solana with their prices, market caps, and volume data."
    )
    args_schema: ClassVar[Type[BaseModel]] = BirdeyeTokenTrendingInput

    async def _arun(self, limit: int = 10) -> str:
        """Execute the BirdEye token trending lookup asynchronously."""
        try:
            logger.info(f"[LUMOKIT] BirdEye token trending lookup with limit: {limit}")

            # Validate and cap the limit
            if limit <= 0:
                limit = 10
            if limit > 20:
                limit = 20

            # Construct the API URL for BirdEye
            api_url = f"https://public-api.birdeye.so/defi/token_trending?sort_by=rank&sort_type=asc&offset=0&limit={limit}"

            # Make the API request
            headers = {
                "X-API-KEY": CONFIG.BIRDEYE_API_KEY,
                "accept": "application/json",
                "x-chain": "solana",
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, headers=headers) as response:
                    if response.status != 200:
                        logger.error(
                            f"[LUMOKIT] Error fetching BirdEye trending data: {response.status} - {await response.text()}"
                        )
                        return f"Failed to get trending tokens data"

                    trending_data = await response.json()

            # Check if the data is valid
            if (
                not trending_data.get("success")
                or "data" not in trending_data
                or "tokens" not in trending_data["data"]
            ):
                logger.error(
                    f"[LUMOKIT] Invalid response format from BirdEye trending API"
                )
                return "Failed to parse trending tokens data"

            # Extract tokens data
            tokens = trending_data["data"]["tokens"]
            if not tokens:
                return "No trending tokens found at this time"

            # Format the response as a readable summary
            summary = f"## Top {len(tokens)} Trending Tokens on Solana (Updated: {trending_data['data']['updateTime']})\n\n"

            for token in tokens:
                price_change = token.get("price24hChangePercent", 0)
                price_change_str = (
                    f"{price_change:+.2f}%" if price_change is not None else "N/A"
                )
                price_change_emoji = (
                    "🔥"
                    if price_change and price_change > 20
                    else "📈"
                    if price_change and price_change > 0
                    else "📉"
                    if price_change and price_change < 0
                    else ""
                )

                volume_change = token.get("volume24hChangePercent", 0)
                volume_change_str = (
                    f"{volume_change:+.2f}%" if volume_change is not None else "N/A"
                )

                summary += f"### {token['rank']}. {token['name']} ({token['symbol']})\n"
                summary += f"- **Price**: ${token['price']:.6f} ({price_change_str}) {price_change_emoji}\n"
                summary += f"- **Market Cap**: ${token.get('marketcap', 0):,.2f}\n"
                summary += f"- **24h Volume**: ${token.get('volume24hUSD', 0):,.2f} ({volume_change_str})\n"
                summary += f"- **Liquidity**: ${token.get('liquidity', 0):,.2f}\n"
                summary += f"- **Contract**: `{token['address']}`\n\n"

            return summary

        except Exception as e:
            logger.error(f"[LUMOKIT] Error in BirdEye token trending tool: {str(e)}")
            return "Failed to get trending tokens data due to an error"

    def _run(self, limit: int = 10) -> str:
        """Synchronous version not implemented."""
        raise NotImplementedError("This tool only supports async execution.")


#################################################
#### BIRDEYE ALL TIME TRADES TOOL ####
#################################################


class BirdeyeAllTimeTradesInput(BaseModel):
    """Input for the BirdEye all time trades tool."""

    token_address: str = Field(
        description="The token address to get all time trade data for"
    )


class BirdeyeAllTimeTradesTool(BaseTool):
    """Tool for getting all time trade statistics for a token on Solana from BirdEye."""

    name: ClassVar[str] = "birdeye_all_time_trades_tool"
    description: ClassVar[str] = (
        "Get comprehensive trade statistics (buys, sells, volumes) of all time for a specific token on Solana."
    )
    args_schema: ClassVar[Type[BaseModel]] = BirdeyeAllTimeTradesInput

    async def _arun(self, token_address: str) -> str:
        """Execute the BirdEye all time trades lookup asynchronously."""
        try:
            logger.info(
                f"[LUMOKIT] BirdEye all time trades lookup for token: {token_address}"
            )

            # Validate the token address (basic check)
            if not token_address or len(token_address) < 32:
                return "Invalid token address. Please provide a valid Solana token address."

            # Construct the API URL for BirdEye
            api_url = f"https://public-api.birdeye.so/defi/v3/all-time/trades/single?time_frame=alltime&address={token_address}"

            # Make the API request
            headers = {
                "X-API-KEY": CONFIG.BIRDEYE_API_KEY,
                "accept": "application/json",
                "x-chain": "solana",
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, headers=headers) as response:
                    if response.status != 200:
                        logger.error(
                            f"[LUMOKIT] Error fetching BirdEye all time trades data: {response.status} - {await response.text()}"
                        )
                        return f"Failed to get trade data for the token"

                    trades_data = await response.json()

            # Check if the data is valid
            if (
                not trades_data.get("success")
                or "data" not in trades_data
                or not trades_data["data"]
            ):
                logger.error(
                    f"[LUMOKIT] Invalid response format from BirdEye all time trades API"
                )
                return "No trade data found for this token"

            # Extract trade data
            trade_stats = trades_data["data"][0]

            # Format the response as a comprehensive summary
            summary = f"## All-Time Trading Statistics for Token\n\n"
            summary += f"This token (`{trade_stats['address']}`) has seen significant trading activity on Solana. "
            summary += f"There have been a total of **{trade_stats['total_trade']:,}** trades, "
            summary += f"with **{trade_stats['buy']:,}** buy transactions and **{trade_stats['sell']:,}** sell transactions. "

            # Add volume information
            token_volume = trade_stats["total_volume"]
            usd_volume = trade_stats["total_volume_usd"]
            summary += (
                f"\n\nThe total trading volume is **{token_volume:,.2f}** tokens "
            )
            summary += f"(approximately **${usd_volume:,.2f}** USD). "

            # Add buy/sell breakdown
            buy_volume_token = trade_stats["volume_buy"]
            sell_volume_token = trade_stats["volume_sell"]
            buy_volume_usd = trade_stats["volume_buy_usd"]
            sell_volume_usd = trade_stats["volume_sell_usd"]

            summary += f"This breaks down to **{buy_volume_token:,.2f}** tokens bought (${buy_volume_usd:,.2f} USD) "
            summary += f"and **{sell_volume_token:,.2f}** tokens sold (${sell_volume_usd:,.2f} USD)."

            # Calculate and add buy/sell ratio
            buy_sell_ratio = (
                trade_stats["buy"] / trade_stats["sell"]
                if trade_stats["sell"] > 0
                else 0
            )
            summary += (
                f"\n\nThe buy-to-sell transaction ratio is **{buy_sell_ratio:.2f}**, "
            )

            if buy_sell_ratio > 1.1:
                summary += (
                    "indicating more buyers than sellers over the token's lifetime."
                )
            elif buy_sell_ratio < 0.9:
                summary += (
                    "indicating more sellers than buyers over the token's lifetime."
                )
            else:
                summary += (
                    "showing a relatively balanced market between buyers and sellers."
                )

            return summary

        except Exception as e:
            logger.error(f"[LUMOKIT] Error in BirdEye all time trades tool: {str(e)}")
            return f"I couldn't retrieve the all-time trading data for this token. This could be due to API limits, network issues, or the token may not exist. Please try again later or verify the token address."

    def _run(self, token_address: str) -> str:
        """Synchronous version not implemented."""
        raise NotImplementedError("This tool only supports async execution.")

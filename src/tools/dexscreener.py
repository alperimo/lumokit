from typing import ClassVar, Type

import aiohttp
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from settings.logger import logger

#################################################
#### DEXSCREENER TOP BOOSTS TOOL ####
#################################################


class DexScreenerTopBoostsInput(BaseModel):
    """Input for the DexScreener Top Boosts tool."""

    limit: int = Field(
        10, description="The number of top boosted tokens to retrieve (default: 10)"
    )


class DexScreenerTopBoostsTool(BaseTool):
    """Tool for getting tokens with the most active boosts on DexScreener."""

    name: ClassVar[str] = "dexscreener_top_boosts_tool"
    description: ClassVar[str] = (
        "Get the tokens with most active boosts on DexScreener, showing popularity and trending projects."
    )
    args_schema: ClassVar[Type[BaseModel]] = DexScreenerTopBoostsInput

    async def _arun(self, limit: int = 10) -> str:
        """Execute the DexScreener top boosts lookup asynchronously."""
        try:
            logger.info(f"[LUMOKIT] DexScreener top boosts lookup, limit: {limit}")

            # Validate the limit parameter
            if limit <= 0:
                limit = 10
            elif limit > 30:
                limit = 30

            # Construct the API URL for DexScreener
            api_url = "https://api.dexscreener.com/token-boosts/top/v1"

            # Make the API request
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url) as response:
                    if response.status != 200:
                        logger.error(
                            f"[LUMOKIT] Error fetching DexScreener top boosts: {response.status} - {await response.text()}"
                        )
                        return f"Failed to get top boosted tokens. The API returned a {response.status} error."

                    data = await response.json()

            # Process the response data
            if not data or not isinstance(data, list):
                return "No top boosted tokens found or invalid data format."

            # Limit the results
            tokens = data[:limit]

            # Format the response
            response_text = f"## Top {len(tokens)} Boosted Tokens on DexScreener\n\n"

            for idx, token in enumerate(tokens, 1):
                chain_id = token.get("chainId", "unknown").capitalize()
                token_address = token.get("tokenAddress", "N/A")
                description = token.get("description", "No description available")
                total_amount = token.get("totalAmount", 0)

                # Trim description if too long
                if len(description) > 150:
                    description = description[:147] + "..."

                response_text += f"### {idx}. Token on {chain_id}\n"
                response_text += f"**Address**: `{token_address}`\n"
                response_text += f"**Boost Amount**: {total_amount}\n"
                response_text += f"**Description**: {description}\n"

                # Add links if available
                links = token.get("links", [])
                if links:
                    response_text += "**Links**:\n"
                    for link in links[:3]:  # Limit to first 3 links
                        link_type = link.get("type", "website")
                        link_label = link.get("label", link_type.capitalize())
                        link_url = link.get("url", "")
                        if link_url:
                            response_text += f"- [{link_label}]({link_url})\n"

                response_text += "\n"

            return response_text

        except Exception as e:
            logger.error(f"[LUMOKIT] Error in DexScreener top boosts tool: {str(e)}")
            return f"Failed to get top boosted tokens. An error occurred: {str(e)}"

    def _run(self, limit: int = 10) -> str:
        """Synchronous version returns a message instead of raising an error."""
        return "This tool only supports asynchronous execution. Please use the async version instead."


#################################################
#### DEXSCREENER TOKEN INFORMATION TOOL ####
#################################################


class DexScreenerTokenInformationInput(BaseModel):
    """Input for the DexScreener Token Information tool."""

    token_addresses: str = Field(
        ...,
        description="Comma-separated list of token addresses to get information about (max 10)",
    )
    chain_id: str = Field("solana", description="The blockchain ID (default: solana)")


class DexScreenerTokenInformationTool(BaseTool):
    """Tool for getting detailed information about tokens from DexScreener."""

    name: ClassVar[str] = "dexscreener_token_information_tool"
    description: ClassVar[str] = (
        "Get detailed DEX information about Solana tokens including price, volume, liquidity, and trading activity."
    )
    args_schema: ClassVar[Type[BaseModel]] = DexScreenerTokenInformationInput

    async def _arun(self, token_addresses: str, chain_id: str = "solana") -> str:
        """Execute the DexScreener token information lookup asynchronously."""
        try:
            logger.info(
                f"[LUMOKIT] DexScreener token information lookup for {token_addresses} on {chain_id}"
            )

            # Parse and validate token addresses
            addresses = [
                addr.strip() for addr in token_addresses.split(",") if addr.strip()
            ]

            if not addresses:
                return "No valid token addresses provided. Please provide at least one token address."

            if len(addresses) > 10:
                addresses = addresses[:10]
                logger.warning(
                    f"[LUMOKIT] Too many token addresses requested, limiting to 10"
                )

            # Format addresses for API request
            formatted_addresses = ",".join(addresses)

            # Construct the API URL
            api_url = f"https://api.dexscreener.com/tokens/v1/{chain_id}/{formatted_addresses}"

            # Make the API request
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url) as response:
                    if response.status != 200:
                        logger.error(
                            f"[LUMOKIT] Error fetching DexScreener token information: {response.status} - {await response.text()}"
                        )
                        return f"Failed to get token information. The API returned a {response.status} error."

                    data = await response.json()

            # Process the response data
            if not data or not isinstance(data, list) or len(data) == 0:
                return "No token information found or invalid data format."

            # Format the response
            response_text = f"## DexScreener Token Information\n\n"

            for pair_info in data:
                chain_id = pair_info.get("chainId", "unknown").capitalize()
                dex_id = pair_info.get("dexId", "unknown").capitalize()

                base_token = pair_info.get("baseToken", {})
                quote_token = pair_info.get("quoteToken", {})

                base_symbol = base_token.get("symbol", "Unknown")
                quote_symbol = quote_token.get("symbol", "Unknown")

                # Extract key information
                price_usd = pair_info.get("priceUsd", "N/A")
                price_native = pair_info.get("priceNative", "N/A")

                # Get 24h volume and price change
                volume_24h = pair_info.get("volume", {}).get("h24", "N/A")
                price_change_24h = pair_info.get("priceChange", {}).get("h24", "N/A")

                # Get liquidity information
                liquidity = pair_info.get("liquidity", {})
                liquidity_usd = liquidity.get("usd", "N/A")

                # Get transaction counts
                txns = pair_info.get("txns", {}).get("h24", {})
                buys_24h = txns.get("buys", "N/A")
                sells_24h = txns.get("sells", "N/A")

                # Extract market cap and FDV if available
                market_cap = pair_info.get("marketCap", "N/A")
                fdv = pair_info.get("fdv", "N/A")

                # Format pair information
                response_text += (
                    f"### {base_symbol}/{quote_symbol} on {dex_id} ({chain_id})\n"
                )

                if price_usd != "N/A":
                    response_text += f"**Price (USD)**: ${price_usd}\n"
                if price_native != "N/A":
                    response_text += (
                        f"**Price ({quote_symbol})**: {price_native} {quote_symbol}\n"
                    )

                if price_change_24h != "N/A":
                    # Format with + sign for positive values
                    sign = "+" if float(price_change_24h) > 0 else ""
                    response_text += f"**24h Change**: {sign}{price_change_24h}%\n"

                if volume_24h != "N/A":
                    response_text += (
                        f"**24h Volume**: ${volume_24h:,.2f}\n"
                        if isinstance(volume_24h, (int, float))
                        else f"**24h Volume**: ${volume_24h}\n"
                    )

                if liquidity_usd != "N/A":
                    response_text += (
                        f"**Liquidity**: ${liquidity_usd:,.2f}\n"
                        if isinstance(liquidity_usd, (int, float))
                        else f"**Liquidity**: ${liquidity_usd}\n"
                    )

                if buys_24h != "N/A" and sells_24h != "N/A":
                    total_txns = (
                        buys_24h + sells_24h
                        if isinstance(buys_24h, int) and isinstance(sells_24h, int)
                        else "N/A"
                    )
                    if total_txns != "N/A":
                        response_text += f"**24h Transactions**: {total_txns} ({buys_24h} buys, {sells_24h} sells)\n"

                if market_cap != "N/A":
                    response_text += (
                        f"**Market Cap**: ${market_cap:,.2f}\n"
                        if isinstance(market_cap, (int, float))
                        else f"**Market Cap**: ${market_cap}\n"
                    )

                if fdv != "N/A":
                    response_text += (
                        f"**Fully Diluted Value**: ${fdv:,.2f}\n"
                        if isinstance(fdv, (int, float))
                        else f"**Fully Diluted Value**: ${fdv}\n"
                    )

                # Add DEX link
                dex_url = pair_info.get("url")
                if dex_url:
                    response_text += f"**DexScreener Link**: [View Pair]({dex_url})\n"

                response_text += "\n"

            return response_text

        except Exception as e:
            logger.error(
                f"[LUMOKIT] Error in DexScreener token information tool: {str(e)}"
            )
            return f"Failed to get token information. An error occurred: {str(e)}"

    def _run(self, token_addresses: str, chain_id: str = "solana") -> str:
        """Synchronous version returns a message instead of raising an error."""
        return "This tool only supports asynchronous execution. Please use the async version instead."

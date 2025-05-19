from typing import ClassVar, Type

import aiohttp
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from settings.logger import logger

#################################################
#### RUGCHECK TOKEN INFORMATION TOOL ####
#################################################


class RugcheckTokenInformationInput(BaseModel):
    """Input for the rugcheck token information tool."""

    token_address: str = Field(
        ..., description="The token address to check on rugcheck.xyz"
    )


class RugcheckTokenInformationTool(BaseTool):
    """Tool for getting token information and top holders using rugcheck.xyz."""

    name: ClassVar[str] = "rugcheck_token_information_tool"
    description: ClassVar[str] = (
        "Get detailed token information including creator details, supply, top holders, and insiders information. Provides insights about token creator, active supply, insider holders, and liquidity markets."
    )
    args_schema: ClassVar[Type[BaseModel]] = RugcheckTokenInformationInput

    async def _arun(self, token_address: str) -> str:
        """Execute the rugcheck token information lookup asynchronously."""
        try:
            logger.info(
                f"[LUMOKIT] Rugcheck token information lookup for: {token_address}"
            )

            # Clean up the token address (remove spaces)
            token_address = token_address.strip()

            # Construct the API URL for rugcheck
            api_url = f"https://api.rugcheck.xyz/v1/tokens/{token_address}/report"

            # Make the API request
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url) as response:
                    if response.status != 200:
                        logger.error(
                            f"[LUMOKIT] Error fetching rugcheck data: {response.status} - {await response.text()}"
                        )
                        return f"Failed to get information for token {token_address}. The token may not exist or the rugcheck service is unavailable."

                    data = await response.json()

            # Extract relevant information from the response
            token_name = data.get("tokenMeta", {}).get("name", "Unknown")
            token_symbol = data.get("tokenMeta", {}).get("symbol", "Unknown")
            creator_address = data.get("creator", "Unknown")
            creator_balance = data.get("creatorBalance", 0)

            # Token supply information
            token_info = data.get("token", {})
            total_supply = token_info.get("supply", 0)
            decimals = token_info.get("decimals", 0)

            # Format the supply to show the actual amount with decimals
            if total_supply and decimals:
                formatted_supply = total_supply / (10**decimals)
                supply_str = f"{formatted_supply:,.2f}"
            else:
                supply_str = "Unknown"

            # Top holders information
            top_holders = data.get("topHolders", [])
            top_holders_info = []

            # Format the top 10 holders (or less if there aren't 10)
            for i, holder in enumerate(top_holders[:10]):
                address = holder.get("address", "Unknown")
                ui_amount = holder.get("uiAmount", 0)
                percent = holder.get("pct", 0)
                insider = holder.get("insider", False)

                holder_str = f"{i + 1}. Address: {address} - {ui_amount:,.2f} tokens ({percent:.2f}%)"
                if insider:
                    holder_str += " [INSIDER]"

                top_holders_info.append(holder_str)

            # Markets information
            markets = data.get("markets", [])
            market_info = []

            for market in markets[:3]:  # Show top 3 markets
                pubkey = market.get("pubkey", "Unknown")
                market_type = market.get("marketType", "Unknown")
                base_usd = market.get("lp", {}).get("baseUSD", 0)
                quote_usd = market.get("lp", {}).get("quoteUSD", 0)
                total_liquidity = base_usd + quote_usd

                market_str = f"Market {pubkey[:8]}...{pubkey[-4:]} ({market_type}): ${total_liquidity:,.2f} liquidity"
                market_info.append(market_str)

            # Create the summary
            summary = [
                f"Token Information for {token_name} ({token_symbol}):",
                f"Contract Address: {token_address}",
                f"Creator Address: {creator_address}",
                f"Creator Balance: {creator_balance:,.2f} tokens",
                f"Total Supply: {supply_str} tokens",
                f"Decimals: {decimals}",
                "",
                "Top Holders:",
            ]

            summary.extend(top_holders_info)

            if market_info:
                summary.append("")
                summary.append("Top Markets:")
                summary.extend(market_info)

            # Rugcheck risk assessment
            risks = data.get("risks", [])
            score = data.get("score", 0)

            summary.append("")
            summary.append(f"Rugcheck Score: {score}")

            if risks:
                summary.append("Identified Risks:")
                for risk in risks:
                    summary.append(f"- {risk}")

            return "\n".join(summary)

        except Exception as e:
            logger.error(
                f"[LUMOKIT] Error in rugcheck token information tool: {str(e)}"
            )
            # Return a user-friendly message instead of raising an error
            return f"Unable to retrieve information from rugcheck.xyz at this time. Please try again later or check if the token address is valid."

    def _run(self, token_address: str) -> str:
        """Synchronous version not implemented."""
        raise NotImplementedError("This tool only supports async execution.")

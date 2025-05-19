from typing import ClassVar, Type

import aiohttp
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from settings.logger import logger

#################################################
#### FLUXBEAM TOKEN PRICE TOOL ####
#################################################


class FluxBeamTokenPriceInput(BaseModel):
    """Input for the FluxBeam token price tool."""

    token_address: str = Field(
        ..., description="The token address to check price on FluxBeam"
    )


class FluxBeamTokenPriceTool(BaseTool):
    """Tool for getting the current price of a token in USD using FluxBeam."""

    name: ClassVar[str] = "fluxbeam_token_price_tool"
    description: ClassVar[str] = (
        "Get the current price of a token in USD (USD) from FluxBeam."
    )
    args_schema: ClassVar[Type[BaseModel]] = FluxBeamTokenPriceInput

    async def _arun(self, token_address: str) -> str:
        """Execute the FluxBeam token price lookup asynchronously."""
        try:
            logger.info(f"[LUMOKIT] FluxBeam token price lookup for: {token_address}")

            # Clean up the token address (remove spaces)
            token_address = token_address.strip()

            # Construct the API URL for FluxBeam
            api_url = f"https://data.fluxbeam.xyz/tokens/{token_address}/price"

            # Make the API request
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url) as response:
                    if response.status != 200:
                        logger.error(
                            f"[LUMOKIT] Error fetching FluxBeam price data: {response.status} - {await response.text()}"
                        )
                        return f"Failed to get token price of that token. The API returned a {response.status} error."

                    price_data = await response.text()

            try:
                # Convert the price data to float and format to 5 decimals
                price = float(price_data)
                formatted_price = "{:.5f}".format(price)
                return f"The current price of the token is {formatted_price} USD (5 decimals)"
            except ValueError:
                logger.error(
                    f"[LUMOKIT] Error parsing FluxBeam price data: {price_data}"
                )
                return "Failed to get token price of that token. The price data couldn't be parsed as a number."

        except Exception as e:
            logger.error(f"[LUMOKIT] Error in FluxBeam token price tool: {str(e)}")
            return (
                f"Failed to get token price of that token. An error occurred: {str(e)}"
            )

    def _run(self, token_address: str) -> str:
        """Synchronous version returns a message instead of raising an error."""
        return "This tool only supports asynchronous execution. Please use the async version instead."

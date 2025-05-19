import asyncio

import aiohttp

DEFAULT_TIMEOUT = 600  # 5 mins timeout


class Requests:
    def __init__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT)
        )

    async def get(self, url, params=None, headers=None, **kwargs):
        async with self.session.get(
            url, params=params, headers=headers, **kwargs
        ) as response:
            return await self._process_response(response)

    async def post(self, url, data=None, headers=None, **kwargs):
        async with self.session.post(
            url, data=data, headers=headers, **kwargs
        ) as response:
            return await self._process_response(response)

    async def put(self, url, data=None, headers=None, **kwargs):
        async with self.session.put(
            url, data=data, headers=headers, **kwargs
        ) as response:
            return await self._process_response(response)

    async def delete(self, url, headers=None, **kwargs):
        async with self.session.delete(url, headers=headers, **kwargs) as response:
            return await self._process_response(response)

    async def _process_response(self, response):
        response_text = await response.text()
        return {
            "status_code": response.status,
            "headers": dict(response.headers),
            "body": response_text,
        }

    async def close(self):
        await self.session.close()


async def requests_stream(url, json: dict = None, headers: dict = None):
    async with aiohttp.ClientSession(raise_for_status=True) as session:
        async with session.post(url, json=json, headers=headers) as r:
            async for line in r.content.iter_any():
                await asyncio.sleep(0.1)
                yield line

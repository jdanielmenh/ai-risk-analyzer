import asyncio

from clients.fmp_client import FMPClient


async def demo():
    api = FMPClient()
    news = await api.articles()
    print(news)


asyncio.run(demo())

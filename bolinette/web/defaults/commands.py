import asyncio

from aiohttp import web

from bolinette.core import Logger
from bolinette.web.resources import WebResources


async def run_server(resources: WebResources, logger: Logger[WebResources]) -> None:
    runner = web.AppRunner(resources.web_app)
    await runner.setup()
    site = web.TCPSite(runner)
    try:
        logger.info(f"Running development server on {site.name}")
        await site.start()
        await asyncio.Event().wait()
    finally:
        logger.info("Shutting down server gracefully")
        await runner.cleanup()

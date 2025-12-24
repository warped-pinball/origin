"""Standalone UDP service entrypoint.

This module forwards UDP discovery and game state messages to the main app
API. It is designed to run in its own container so the API / web UI can remain
isolated from the UDP workload.
"""

import asyncio
import logging
import signal
from collections.abc import Sequence

from . import udp

from .ray_client import RayApiClient

logger = logging.getLogger(__name__)


async def _close_transports(transports: Sequence[asyncio.DatagramTransport]) -> None:
    for transport in transports:
        transport.close()


async def run_service() -> None:
    handler = RayApiClient()
    transports = await udp.start_udp_servers(handler=handler)
    logger.info("UDP transports started: %s", [transport.get_extra_info("sockname") for transport in transports])

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:  # pragma: no cover - platform dependent
            pass

    try:
        await stop_event.wait()
    finally:
        await _close_transports(transports)


def main() -> None:
    asyncio.run(run_service())


if __name__ == "__main__":  # pragma: no cover - manual execution guard
    main()

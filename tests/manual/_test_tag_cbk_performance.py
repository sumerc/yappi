import time
from contextvars import ContextVar
from typing import Dict, Tuple

import fastapi
import yappi
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp
from yappi import YFuncStats

yappi_request_id = ContextVar('yappi_request_id')
yappi_request_id.set(-10)


def get_context_id() -> int:
    try:
        return yappi_request_id.get()
    except LookupError:
        return -2


yappi.set_tag_callback(get_context_id)


class BenchMiddleware(BaseHTTPMiddleware):

    def __init__(self, app: ASGIApp, calls_to_track: Dict[str, str]) -> None:
        self.calls_to_track = calls_to_track
        super().__init__(app, None)

    async def dispatch(self, request: Request, call_next) -> Response:
        ctx_id = id(request)
        yappi_request_id.set(ctx_id)
        assert yappi_request_id.get() == ctx_id
        response = await call_next(request)
        tracked_stats: Dict[str, YFuncStats] = {}

        for name, call_to_track in self.calls_to_track.items():
            tracked_stats[name] = yappi.get_func_stats(
                {
                    "name": call_to_track,
                    "tag": ctx_id
                }
            )
        server_timing = []
        for name, stats in tracked_stats.items():
            if not stats.empty():
                server_timing.append(f"{name}={(stats.pop().ttot * 1000):.3f}")
        if server_timing:
            response.headers["Server-Timing"] = ','.join(server_timing)
        #yappi.clear_stats()
        return response


# ######################
# ##### Usage test #####
# ######################
import asyncio

from httpx import AsyncClient
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def context_id_endpoint() -> Tuple[int, float]:
    start = time.time()
    await asyncio.sleep(1)
    end = time.time()
    return get_context_id(), end - start


track: Dict[str, str] = {
    "endpoint": context_id_endpoint.__qualname__,
    "pydantic": fastapi.routing.serialize_response.__qualname__,
    "render": Response.render.__qualname__,
    "dispatch": BenchMiddleware.dispatch.__qualname__
}

app.add_middleware(BenchMiddleware, calls_to_track=track)


async def main():
    start = time.time()
    yappi.set_clock_type("wall")
    yappi.start()  # If you don't start yappi, stats.empty() will always be true
    client = AsyncClient(app=app, )
    async with client:
        tasks = [client.get("http://www.example.org/") for _ in range(1000)]
        resps = await asyncio.gather(*tasks)
        for resp in resps:
            print(f"Request ID: {resp.json()[0]}")
            print(f"Actual timing: {resp.json()[1]* 1000:>8.3f}")
            print(f"Server Timing: {resp.headers.get('server-timing')}")
            print("-----")
    end = time.time()
    print(f"TOTAL:{end-start:>8.3f}")


if __name__ == '__main__':
    asyncio.run(main())
    yappi.stop()

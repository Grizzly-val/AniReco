from contextlib import asynccontextmanager
import json
from typing import TypedDict, cast
from fastapi import FastAPI, HTTPException, Depends, Request, status

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.schemas import LayerOneParameters

import asyncio
import httpx

from Logs import Logger
import logging

from redis.asyncio import Redis


from src.dependencies import get_client, get_redis

from urllib.parse import urlencode


# Logging for debugging
app_logger = Logger(logger_name='app_logger', log_file='app.log').get_logger()
def get_app_logger() -> Logger:
    return app_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    
    app.state.client = httpx.AsyncClient(timeout=httpx.Timeout(10.0))
    app.state.redis = Redis(host="localhost", port=6379, decode_responses=True)
    app_logger.info("HTTP client started")
    app_logger.info("Redis connection started")

    yield

    await app.state.client.aclose()
    await app.state.redis.close()
    app_logger.info("Redis connection closed")
    app_logger.info("HTTP client closed")


# ===================================
app = FastAPI(lifespan=lifespan)
JIKAN_URL = "https://api.jikan.moe/v4"
# ===================================


@app.exception_handler(RequestValidationError)
async def request_validation(request: Request, exc: RequestValidationError):
    app_logger.warning(f"User sent bad data: {exc.errors()}")

    return JSONResponse(
        content = {"message": "You've entered invalid filter/s", "details": exc.errors()},
        status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    )

# @app.exception_handler(HTTPException) Not now

async def fetch_jikan(request_url: str, client: httpx.AsyncClient) -> httpx.Response:
    try:
        app_logger.info(f"Fetching Jikan | URL: {request_url}")
        response = await client.get(request_url)
        response.raise_for_status()

    except httpx.HTTPStatusError as httpError:
        app_logger.warning(f"Fetch failed!  | HTTPStatus: {response.status_code}")
    else:
        app_logger.info(f"Fetch successful! | HTTPStatus: {response.status_code}")
    finally:
        return response

async def check_redis(request_url: str, params: dict, redis: Redis):
    return await redis.get()
    ...


"""
========================  TODO : CACHING ========================
Datas to cache:
    Request-Level Caching (Reactive Caching): Cache specific requests, including all parameters. Proposed TTL: (5 minutes)
    Proactive caching: IDK

    
    --------------------------------DONE ALMOST---------------------------------------
    Layer 1:
    > Narrow down to (status, order_by, type, sfw), cache then return
    -------------------------------NOT DONE----------------------------------------
    Layer 2:        
    > Narrow down by filtering constraints
    -----------------------------------------------------------------------

================================================================
"""





# TODO (infra/typing):
# httpx client and Redis are created in the app lifespan and stored on app.state.
# This works at runtime, but app.state is dynamically typed, so the IDE does not
# recognize `client` as httpx.AsyncClient or `redis` as Redis.
#
# Revisit later:
# - Decide whether to wrap these in typed dependencies (Request + Depends)
# - Or define a typed AppState and cast app.state for better autocomplete
# - Goal: make the codebase *know* these are an HTTP client and a Redis connection,
#   not just "some object living on app.state"



async def handle_request(client: httpx.AsyncClient, redis: Redis, lf: LayerOneParameters) -> tuple[dict, httpx.Response]:
    params = lf.model_dump(exclude_none=True, exclude={"subject"}, mode="json")
    query_string = urlencode(params)
    request_url = f"{JIKAN_URL}/{lf.subject.value}?{query_string}" 


    l1_cache = await redis.get(request_url)
    
    cache_ttl = 30

    if l1_cache is not None:
        app_logger.info(f"Cache hit for {request_url}")
        # Extend TTL: 'expire' resets the timer without changing the value
        await redis.expire(request_url, cache_ttl)
        # Convert bytes from Redis back to a Python Dict
        return json.loads(l1_cache)
    
    try:
        app_logger.info(f"Cache miss. Fetching from Jikan...")
        jikan_response = await fetch_jikan(request_url, client)
        data = jikan_response.json()

        jikan_response.raise_for_status()
    except httpx.HTTPStatusError as httpError:
        app_logger.warning(f"Caching cancelled: HTTP Status Error Occured")
        return data
    except Exception as e:
        app_logger.warning(f"Caching cancelled: Unknown Error Occured: {e}")
        return data

    app_logger.info(f"Caching query results")
    json_string = json.dumps(data)
    await redis.set(name=request_url, value=json_string, ex=cache_ttl)

    return data



    
    






@app.post("/get_recommendation", status_code=200)
async def get_recommendation(lf: LayerOneParameters, client: httpx.AsyncClient = Depends(get_client), redis: Redis = Depends(get_redis)) -> dict:
    response = await handle_request(client, redis, lf)
    return response

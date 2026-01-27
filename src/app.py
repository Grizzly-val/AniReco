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


from src.dependencies import ServiceProvider

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
    app_logger.info("Redis connection started\n")

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
    app_logger.warning(f"User sent bad data: {exc.errors()}\n")

    return JSONResponse(
        content = {"message": "You've entered invalid filter/s", "details": exc.errors()},
        status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    )



@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # Log the actual detail (which is what you passed to 'detail=...')
    app_logger.warning(f"HTTP Error {exc.status_code}: {exc.detail}\n")

    return JSONResponse(
        status_code=exc.status_code, # Use the status code from the exception!
        content={
            "status_code": exc.status_code,
            "detail": exc.detail,
        }
    )




async def fetch_jikan(request_url: str, client: httpx.AsyncClient) -> httpx.Response:
    try:
        app_logger.info(f"Fetching Jikan | URL: {request_url}")
        response = await client.get(request_url)
        json_response = response.json()
        response.raise_for_status()

        if isinstance(json_response, dict) and "status" in json_response and json_response.get("status", 200) >= 400:
            app_logger.warning(f"Fetch failed!  | HTTPStatus: {json_response["status"]}")
            raise HTTPException(status_code=json_response.get("status", 400))
        
        app_logger.info(f"Fetch successful! | HTTPStatus: {response.status_code}")

        return response
    except httpx.HTTPStatusError as e:
            app_logger.error(f"Upstream HTTP Error: {e.response.status_code}")
            raise HTTPException(status_code=e.response.status_code, detail="Jikan Server Error",)
    

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



async def layer_one_handler(services: ServiceProvider, l1_params: LayerOneParameters) -> dict:
    client = services.client
    redis = services.redis

    params = l1_params.model_dump(exclude_none=True, exclude={"subject"}, mode="json")
    query_string = urlencode(params)
    request_url = f"{JIKAN_URL}/{l1_params.subject.value}?{query_string}" 


    l1_cache = await redis.get(request_url)
    
    ttl = 30

    if l1_cache is not None:
        app_logger.info(f"Cache hit for {request_url}")
        app_logger.info(f"Fetching from cache\n")
        # Extend TTL: 'expire' resets the timer without changing the value
        await redis.expire(request_url, ttl)
        # Convert bytes from Redis back to a Python Dict
        return json.loads(l1_cache)
    
    try:
        app_logger.info(f"Cache miss. Fetching from Jikan...")
        jikan_response = await fetch_jikan(request_url, client)
        jikan_response.raise_for_status()

        data = jikan_response.json()
    except HTTPException as httpError:
        app_logger.warning(f"Caching cancelled: HTTP Status Error Occured")
        raise
    except Exception as e:
        app_logger.warning(f"Caching cancelled: Unknown Error Occured: {e}")
        raise HTTPException(status_code=500, detail={"Unknown Error": "unknown"})
    else:
        app_logger.info(f"Caching query results\n")
        json_string = json.dumps(data)
        await redis.set(name=request_url, value=json_string, ex=ttl)

        return data


async def layer_two_handler(services: ServiceProvider) -> dict:
    ... 

    
    






@app.post("/get_recommendation", status_code=200)
async def get_recommendation(l1_params: LayerOneParameters, services: ServiceProvider = Depends()) -> dict:
    l1_response = await layer_one_handler(services, l1_params)
    return l1_response

    # l2_response = await layer_two_handler()

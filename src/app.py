from contextlib import asynccontextmanager
import json
from typing import TypedDict, cast
from fastapi import FastAPI, HTTPException, Depends, Request, status

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.schemas import AnimeParams, MangaParams

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
    




async def get_cache_validation(hot_params: dict, request_hotness: int, jikan_response: httpx.Response) -> dict:

    json_data = jikan_response.json()
    app_logger.info(request_hotness + 1)
    if request_hotness > 5:
        return {"layer": "l2", "ttl": 120, "description": "hot_request"}
  

    data_len = len(json_data["data"])



    # check if request gives negative data
    if data_len == 0:
        return {"layer":"l1", "ttl": 60, "description":"negative_cache"}

    
    total = 0
    for hotness in hot_params.values():
        total += hotness
    avg = total / len(hot_params)
    if avg > 10:
        return {"layer": "l2", "ttl": 150, "description": "hot_params"}
    

    return {"layer":"l1", "ttl": 60, "description": "regular_cache"}








async def request_handler(params: AnimeParams | MangaParams, services: ServiceProvider) -> dict:

    # status
    # order_by
    # genres
    # type
    # rating
    
    redis = services.redis

    parsed_params = params.model_dump(mode="json", exclude_none=True)
    parsed_params = dict(sorted(parsed_params.items()))

    string_params = urlencode(parsed_params)
    
    request_url = f"{JIKAN_URL}/anime?{string_params}"

    hotness_key = f"hot:{request_url}"
    await redis.incr(name=hotness_key)
    await redis.expire(hotness_key, 60)
    temp = await redis.get(name=hotness_key)
    request_hotness = int(temp)

    cache_priorities = {"status", "order_by", "genres", "type", "rating"}
    # Create hotness cache for each priority params to track hotness

    # l1_cache : Longer TTL                     [900]
    # l2_cache : Shorter TTL (still redis)      [120]
    # Decide cache tier based on query entropy, hotness, and result breadth
    hot_params = {}
    for cp in cache_priorities:
        value_of_priority = parsed_params.get(cp)
        if value_of_priority is not None:
            await redis.incr(name=f"anime:{cp}:{value_of_priority}")
            await redis.expire(f"anime:{cp}:{value_of_priority}", 60)
            val = await redis.get(f"anime:{cp}:{value_of_priority}")
            hot_params[f"{cp}:{value_of_priority}"] = int(val)
        
    
    
    l1_cache = await redis.get(f"l1:{request_url}")

    if l1_cache:
        return json.loads(l1_cache)

    l2_cache = await redis.get(f"l2:{request_url}")

    if l2_cache:
        return json.loads(l2_cache)
    
    try:
        jikan_response: httpx.Response = await fetch_jikan(request_url=request_url, client=services.client)
        cache_status: dict = await get_cache_validation(hot_params, request_hotness, jikan_response)
        
        cache_key: str = f"{cache_status["layer"]}:{request_url}"
        cache_ttl: int = cache_status["ttl"]
        
        data_response: dict = jikan_response.json()

        await redis.set(name=cache_key, value=json.dumps(data_response))
        await redis.expire(name=cache_key, time=cache_ttl)
        
        return data_response
    
    except HTTPException:
        raise
    except httpx.HTTPStatusError:
        raise
    # except Exception:
    #     raise HTTPException(status_code=404, detail="Unknown Error")
    # General exception removed cuz it gets in the way of debugging
    



@app.post("/get_recommendation/anime", status_code=200)
async def get_recommendation(params: AnimeParams, services: ServiceProvider = Depends(ServiceProvider)) -> dict:
    result = request_handler(params=params, services=services)
    return await result

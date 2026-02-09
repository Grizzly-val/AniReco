from contextlib import asynccontextmanager
import time
import json
from fastapi import FastAPI, HTTPException, Depends

from src.tools.crafters import craft_key
from src.data.schemas import AnimeParams, MangaParams
from src.cache.redis_database import get_cache_level
from src.dependencies.services import ServiceProvider
from src.tools.Logs import Logger

import httpx

from redis.asyncio import Redis






# Logging for debugging
app_logger = Logger(logger_name='app_logger', log_file='app.log').get_logger()


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


async def fetch_jikan(request_url: str, client: httpx.AsyncClient, params: dict = None) -> httpx.Response:
    try:
        response = await client.get(url=request_url, params=params)
        json_response = response.json()
        response.raise_for_status()

        if isinstance(json_response, dict) and "status" in json_response and json_response.get("status", 200) >= 400:
            app_logger.warning(f"Fetch failed! {request_url} | HTTPStatus: {json_response["status"]}")
            raise HTTPException(status_code=json_response.get("status", 400))
        
        app_logger.info(f"Fetch successful! {response.url} | HTTPStatus: {response.status_code}")

        return response
    
    except httpx.HTTPStatusError as e:
            app_logger.error(f"Upstream HTTP Error: {e.response.status_code}")
            raise HTTPException(status_code=e.response.status_code, detail="Jikan Server Error",)
    


async def paramsID_lookup(param_string: list[str], services: ServiceProvider, lookup_name: str) -> list[int] | None:

    look_ups = {
        "lookup:genres:manga":"https://api.jikan.moe/v4/genres/anime",
        "lookup:genres:anime":"https://api.jikan.moe/v4/genres/manga"
    }

    redis = services.redis
    client = services.client
    
    table_name = f"lookup:{lookup_name}"
    lookup_exists = await redis.exists(table_name)
    if not lookup_exists:
        app_logger.info(f"Genre lookup table not found")
        req_url = look_ups[table_name]
        fresh_lookup = await fetch_jikan(request_url=req_url, client=client)
        new_lookup = fresh_lookup.json()["data"]
        for i in new_lookup:
            k: str = i["name"]
            v: int = i["mal_id"]

            await redis.hsetnx(name=table_name, key=k.lower(), value=v)
            await redis.expire(name=table_name, time=10000)
        app_logger.info(f"Fetched and cached genre lookup")

    params_int = []
    for ps in param_string:
        id = await redis.hget(name=table_name, key=ps.lower())
        params_int.append(int(id))
    app_logger.info(f"String genres converted to int mal_id")
    return params_int


async def reco_request_handler(params: AnimeParams | MangaParams, services: ServiceProvider) -> dict:

    parsed_params = params.model_dump(mode="json", exclude_none=True)
    genres = parsed_params["genres"]
    
    if genres:
        genres_int = await paramsID_lookup(param_string=genres, services=services, lookup_name="genres:anime")
        if genres_int:
            parsed_params["genres"] = ",".join(map(str, genres_int))

    
    request_name = craft_key(parsed_params)

    redis = services.redis
    

    hotness_key = f"hot_request|{request_name}"
    await redis.incr(name=hotness_key)
    await redis.expire(hotness_key, 60)
    temp = await redis.get(name=hotness_key)
    request_hotness = int(temp)
    app_logger.info(f"{hotness_key} - [{request_hotness}] request counter cached")



    cache_priorities = {"status", "order_by", "genres", "type", "rating"}
    # Create hotness cache for each priority params to track hotness
    hot_params = {}
    for cp in cache_priorities:
        v_priority = parsed_params.get(cp)
        hot_cache_name = f"param_hotness|anime|{cp}:{v_priority}"
        if v_priority is not None:                               # cp for cache_priority
            await redis.incr(name=hot_cache_name)
            await redis.expire(hot_cache_name, 60)
            val = await redis.get(hot_cache_name)
            hot_params[f"{cp}:{v_priority}"] = count = int(val)
            app_logger.info(f"{hot_cache_name} - [{count}] cached!")
        
    
    # l1_cache : Longer TTL
    # l2_cache : Shorter TTL (still redis)
    
    l1_cache = await redis.get(f"l1:{request_name}")

    if l1_cache:
        app_logger.info("l1 cache hit!")
        cache_status: dict = await get_cache_level(hot_params=hot_params, request_hotness=request_hotness)
        cache_key: str = f"{cache_status["layer"]}:{request_name}"
        cache_ttl: int = cache_status["ttl"]
        await redis.setnx(name=cache_key, value=l1_cache)
        await redis.expire(name=cache_key, time=cache_ttl)
        app_logger.info(f"Cached! || key: ({cache_key}) | ttl: ({cache_ttl})")
        return json.loads(l1_cache)
    app_logger.info("l1 cache miss")




    l2_cache = await redis.get(f"l2:{request_name}")

    if l2_cache:
        app_logger.info("l2 cache hit!")
        cache_status: dict = await get_cache_level(hot_params=hot_params, request_hotness=request_hotness)
        cache_key: str = f"{cache_status["layer"]}:{request_name}"
        cache_ttl: int = cache_status["ttl"]
        await redis.setnx(name=cache_key, value=l2_cache)
        await redis.expire(name=cache_key, time=cache_ttl)
        app_logger.info(f"Cached! || key: ({cache_key}) | ttl: ({cache_ttl})")
        return json.loads(l2_cache)
    app_logger.info("l2 cache miss")
    
    try:
        request_url = f"{JIKAN_URL}/anime"
        jikan_response: httpx.Response = await fetch_jikan(request_url=request_url, client=services.client, params=parsed_params)

        cache_status: dict = await get_cache_level(hot_params, request_hotness, jikan_response)
        
        cache_key: str = f"{cache_status["layer"]}:{request_name}"
        cache_ttl: int = cache_status["ttl"]
        
        data_response: dict = jikan_response.json()

        await redis.setnx(name=cache_key, value=json.dumps(data_response))
        await redis.expire(name=cache_key, time=cache_ttl)
        app_logger.info(f"Cached! || key: ({cache_key}) | ttl: ({cache_ttl})")

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
    start_time = time.perf_counter()
    app_logger.info("Request Received!")
    result = await reco_request_handler(params=params, services=services)
    end_time = time.perf_counter()
    app_logger.info(f"Request Handled! ({end_time - start_time:4F}s)\n")
    return result

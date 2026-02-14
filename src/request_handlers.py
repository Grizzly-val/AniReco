import asyncio
import json
from typing import Awaitable, Dict, Callable

from fastapi import HTTPException
import httpx
from src.cache.redis_database import get_cache_level
from src.data.schemas import AnimeParams, MangaParams
from src.dependencies.services import ServiceProvider
from src.jikan import fetch_jikan
from src.lookups import paramsID_lookup
from src.tools.crafters import craft_key

class RequestCollapser:
    def __init__(self):
        self.pendings: dict[str, asyncio.Future] = {}
        self.lock = asyncio.Lock()

    async def run(self, request_name: str, fetch_fun: Callable[[], Awaitable[dict]]):

        # lock to avoid two concurrent request intertwining
        # lock is saying "only one request at a time"
        async with self.lock:
            if request_name not in self.pendings:
                # no similar request = first request = the creator
                loop = asyncio.get_running_loop()
                future = loop.create_future()
                self.pendings[request_name] = future
                creator = True
            else:
                # request exists in pendings = not first = not the creator
                future = self.pendings[request_name]
                creator = False
                # wait for future to be set instead


        if creator:
            try:
                result = await fetch_fun()
                future.set_result(result)   # sets waiting requests free with a future value
            except Exception as e:
                future.set_exception(e)
            finally:
                async with self.lock:
                    self.pendings.pop(request_name, None) # must be removed after process

        # use the one future for all requests
        return await future

req_collapser = RequestCollapser()



"""
TODO: Make this request accept both AnimeParams or MangaParams flexibly
TODO: Return and cache filtered data. Do not return everything.
    ex: 10 per page, filtered "data":{}


"""
async def reco_request_handler(params: AnimeParams | MangaParams, services: ServiceProvider) -> dict:
    

    from src.app import app_logger

    JIKAN_BASE_URL = "https://api.jikan.moe/v4"
    request_url = f"{JIKAN_BASE_URL}/anime"

    parsed_params = params.model_dump(mode="json", exclude_none=True)
    genres = parsed_params.get("genres", None)
    
    if genres:
        genres_int = await paramsID_lookup(param_string=genres, services=services, lookup_name="genres:anime")
        if genres_int:
            parsed_params["genres"] = ",".join(map(str, genres_int))

    
    request_name = f"{request_url}?{craft_key(parsed_params)}"

    redis = services.redis
    
    
    """
    TODO: Suggestion to cache this inside fetch_jikan()
    """
    hotness_key = f"hot_request|{request_name}"
    temp = await redis.incr(name=hotness_key)
    # temp = await redis.get(name=hotness_key)
    request_hotness = int(temp)
    if temp == 1:
        await redis.expire(hotness_key, 60)
    app_logger.info(f"{hotness_key} - [{request_hotness}] request counter cached")



    cache_priorities = {"status", "order_by", "genres", "type", "rating"}
    # Create hotness cache for each priority params to track hotness
    hot_params = {}
    for cp in cache_priorities:
        v_priority = parsed_params.get(cp)
        hot_cache_name = f"param_hotness|anime|{cp}:{v_priority}"
        if v_priority is not None:                               # cp for cache_priority
            val = await redis.incr(name=hot_cache_name)
            await redis.expire(hot_cache_name, 60)
            hot_params[f"{cp}:{v_priority}"] = count = int(val)
            app_logger.info(f"{hot_cache_name} - [{count}] cached!")
        
    
    # l1_cache : Longer TTL
    # l2_cache : Shorter TTL (still redis)
    
    l1_cache = await redis.get(f"l1:{request_name}")
    """
    TODO: L1 should be blazing fast local cache. But not for now
    """
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
    

    

    # Last resort (l1 and l2 miss)
    # Collapse request: If many received for the same request, one computes/fetches, others wait.

    # define fetch function. Will be called by the 'creator'. First to request
    async def fetch_fun():
        try:
            # inside fetch attempt/try

            # exception likely to occur here
            jikan_response: httpx.Response = await fetch_jikan(request_url=request_url, client=services.client, params=parsed_params)


            cache_status: dict = await get_cache_level(hot_params, request_hotness, jikan_response)
            
            cache_key: str = f"{cache_status["layer"]}:{request_name}"
            cache_ttl: int = cache_status["ttl"]
            
            data_response: dict = jikan_response.json()

            # cache if fetch successful
            await redis.setnx(name=cache_key, value=json.dumps(data_response))
            await redis.expire(name=cache_key, time=cache_ttl)
            app_logger.info(f"Cached! || key: ({cache_key}) | ttl: ({cache_ttl})")

            # return to FIRST CALLER of the same request
            return data_response
        except HTTPException:
            raise
        except httpx.HTTPStatusError:
            raise
        # except Exception:
        #     raise HTTPException(status_code=404, detail="Unknown Error")
        # General exception removed cuz it gets in the way of debugging
    # request collapsing logic
    return await req_collapser.run(request_name, fetch_fun)




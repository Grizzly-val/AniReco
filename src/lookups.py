from src.dependencies.services import ServiceProvider
from src.jikan import fetch_jikan

"""LOOKUP FOR ONLY GENRE"""
"""TODO: Add lookup for producers. Tweak this function so it's using the same function"""

async def paramsID_lookup(param_string: list[str], services: ServiceProvider, lookup_name: str) -> list[int] | None:
    from src.app import app_logger

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

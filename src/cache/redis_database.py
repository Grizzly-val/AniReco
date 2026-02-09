import httpx


async def get_cache_level(hot_params: dict, request_hotness: int, jikan_response: httpx.Response = None) -> dict:
    from src.app import app_logger
    if request_hotness > 5:
        app_logger.info("Returning cache for HOT REQUEST")
        return {"layer": "l1", "ttl": 120, "description": "hot_request"}
  
    if jikan_response:
        json_data = jikan_response.json()
        data_len = len(json_data["data"])

        # check if request gives negative data
        if data_len == 0:
            app_logger.info("Returning cache for NEGATIVE CACHE")
            return {"layer":"l2", "ttl": 60, "description":"negative_cache"}

    
    total = 0
    for hotness in hot_params.values():
        total += hotness
    avg = total / len(hot_params)
    if avg > 10:
        app_logger.info("Returning cache for HOT PARAMS")
        return {"layer": "l1", "ttl": 150, "description": "hot_params"}
    

    app_logger.info("Returning cache for REGULAR CACHE")
    return {"layer":"l2", "ttl": 60, "description": "regular_cache"}
from contextlib import asynccontextmanager
import time
from fastapi import FastAPI, Depends


from src.request_handlers import reco_request_handler

from src.data.schemas import AnimeParams, MangaParams
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
# ===================================


    



@app.post("/get_recommendation/anime", status_code=200)
async def get_recommendation(params: AnimeParams, services: ServiceProvider = Depends(ServiceProvider)) -> dict:

    # TODO: MAKE SURE TO RETURN AND CACHE ONLY NECESSARY DATA (Name, Start/End Date, Score, ).

    start_time = time.perf_counter()
    app_logger.info("Request Received!")
    result = await reco_request_handler(params=params, services=services)
    end_time = time.perf_counter()
    app_logger.info(f"Request Handled! ({end_time - start_time:4F}s)\n")
    return result

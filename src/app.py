from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from src.schemas import LookingFor

import asyncio
import httpx

from Logs import Logger
import logging

from redis import Redis






# Logging for debugging
app_logger = Logger(logger_name='app_logger', log_file='app.log').get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.client = httpx.AsyncClient(timeout=httpx.Timeout(10.0))
    app.state.redis = Redis(host="localhost", port=6379)
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








async def fetch_jikan(request_url, params) -> httpx.Response:
    client = app.state.client
    response = await client.get(request_url, params=params)
    if response:
        app_logger.info(f"Fetch successful! | URL: {response.url}")
    return response




"""
========================  TODO : CACHING ========================
Datas to cache:
    Request-Level Caching (Reactive Caching): Cache specific requests, including all parameters. Proposed TTL: (5 minutes)
    Proactive caching: IDK

    
    -----------------------------------------------------------------------
    Layer 1:
    > Narrow down to (status, order_by, type, sfw), cache then return
    -----------------------------------------------------------------------
    Layer 2:
    > Narrow down by filtering constraints
    -----------------------------------------------------------------------


================================================================
"""



@app.post("/get_recommendation", status_code=200)
async def get_recommendation(lf: LookingFor) -> dict:

    params = lf.model_dump(exclude_none=True)           # Turn lf into dictionary then don't put items with value None in the parameters
    # Genres in JikanAPI can be filtered by: genres, themes, explicit_genres, and demographics. Do this in the front-end

    request_url = f"{JIKAN_URL}/{lf.subject}"
    jikan_response = await fetch_jikan(request_url, params)
    
    
    return jikan_response.json()
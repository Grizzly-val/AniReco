from fastapi import Depends, Request
import httpx
from redis.asyncio import Redis


# def get_client(request: Request) -> httpx.AsyncClient:
#     return request.app.state.client                         # Interestingly, request here helps identify the reference from app.py

# def get_redis(request: Request) -> Redis:
#     return request.app.state.redis

# def get_dependencies(request: Request) -> dict:
#     return {"client": Depends(get_client), "redis": Depends(get_redis)} 


class ServiceProvider:
    def __init__(self, request: Request):
        self.client: httpx.AsyncClient = request.app.state.client
        self.redis: Redis = request.app.state.redis
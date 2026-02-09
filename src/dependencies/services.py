from fastapi import Request
import httpx
from redis.asyncio import Redis


class ServiceProvider:
    def __init__(self, request: Request):
        self.client: httpx.AsyncClient = request.app.state.client
        self.redis: Redis = request.app.state.redis
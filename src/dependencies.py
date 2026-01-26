from fastapi import Request
import httpx
from redis.asyncio import Redis


def get_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.client                         # Interestingly, request here helps identify the reference from app.py

def get_redis(request: Request) -> Redis:
    return request.app.state.redis                  
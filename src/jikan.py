from fastapi import HTTPException
import httpx

async def fetch_jikan(request_url: str, client: httpx.AsyncClient, params: dict = None) -> httpx.Response:
    from src.app import app_logger

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
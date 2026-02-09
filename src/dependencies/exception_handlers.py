from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.app import app



@app.exception_handler(RequestValidationError)
async def request_validation(request: Request, exc: RequestValidationError):
    from src.app import app_logger
    
    app_logger.warning(f"User sent bad data: {exc.errors()}\n")

    return JSONResponse(
        content = {"message": "You've entered invalid filter/s", "details": exc.errors()},
        status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    )



@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    from src.app import app_logger

    # Log the actual detail (which is what you passed to 'detail=...')
    app_logger.warning(f"HTTP Error {exc.status_code}: {exc.detail}\n")

    return JSONResponse(
        status_code=exc.status_code, # Use the status code from the exception!
        content={
            "status_code": exc.status_code,
            "detail": exc.detail,
        }
    )
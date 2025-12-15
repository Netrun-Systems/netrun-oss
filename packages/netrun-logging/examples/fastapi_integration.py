"""
FastAPI Integration Example - netrun-logging

Demonstrates middleware integration with FastAPI.
Run with: uvicorn examples.fastapi_integration:app --reload
"""

from fastapi import FastAPI, Depends
from netrun_logging import configure_logging, get_logger
from netrun_logging.middleware import add_logging_middleware
from netrun_logging.correlation import get_correlation_id

# Configure logging first
configure_logging(
    app_name="fastapi-example",
    environment="development",
    log_level="INFO",
)

logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(title="Netrun Logging Example")

# Add logging middleware
add_logging_middleware(app)

@app.get("/")
async def root():
    """Root endpoint."""
    logger.info("Root endpoint called")
    return {"message": "Hello World", "correlation_id": get_correlation_id()}

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    """Get user by ID."""
    logger.info(f"Fetching user", extra={"user_id": user_id})
    return {"user_id": user_id, "name": f"User {user_id}"}

@app.post("/items")
async def create_item(name: str):
    """Create new item."""
    logger.info(f"Creating item", extra={"item_name": name})
    return {"name": name, "status": "created"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

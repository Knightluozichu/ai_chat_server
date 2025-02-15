
import uvicorn
from app.main import app

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=3000,
        log_level="info",
        timeout_keep_alive=30,
        limit_concurrency=100,
        limit_max_requests=10000
    )

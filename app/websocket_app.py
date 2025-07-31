from fastapi import FastAPI
from .database import init_db
from .routers.claim import ws_router

# Initialize database for WebSocket service
init_db()

app = FastAPI(title="Origin WS")
app.include_router(ws_router)

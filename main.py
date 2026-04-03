import uvicorn
from fastapi import FastAPI

import core.config
from api import router as api_router
app = FastAPI()
app.include_router(
    api_router,
    prefix=core.config.settings.api
)

if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)
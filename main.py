import os

if os.getenv('API_ENV') != 'production':
    from dotenv import load_dotenv

    load_dotenv()
    
import uvicorn

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from __version__ import version, title, description
from routers import health, completion

from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

templates = Jinja2Templates(directory="templates")


app = FastAPI(
    title=title,
    version=version,
    description=description,
)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(completion.router)

@app.get("/")
async def root():
    return {"message": "Hello World!"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
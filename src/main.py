from fastapi import FastAPI
from src.events.controller import eventRouter
from src.firecrawl.controller import firecrawlRouter

app = FastAPI()


app.include_router(eventRouter, prefix='/api')

app.include_router(firecrawlRouter, prefix='/api')


@app.get("/")
async def root():
    return {"message": "Hello World"}

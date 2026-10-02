from fastapi import FastAPI
from pydantic import BaseModel
from resolver import resolve_link

app = FastAPI(title="LinkBridge API")

# Request Model
class ResolveRequest(BaseModel):
    long_url: str

@app.get("/")
def health_check():
    return {"service": "LinkBridge", "status": "Running"}


@app.post("/resolve")
def resolve(request: ResolveRequest):
    return resolve_link(request.long_url)
    
    
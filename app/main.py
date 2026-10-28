from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api import routes_reviews, routes_github

app = FastAPI(
    title="CodeSentinel API",
    description="AI-Powered Code Review Engine",
    version="1.0.0"
)

app.include_router(routes_reviews.router, prefix="/api")
app.include_router(routes_github.router, prefix="/api")

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "CodeSentinel"}

# Static files mount karna
app.mount("/", StaticFiles(directory="static", html=True), name="static")
from fastapi import FastAPI

app = FastAPI(
    title="Urumi MCP Gateway",
    description="A gateway for managing and routing MCP tool calls",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/")
def root():
    return {"message": "Welcome to the Urumi MCP Gateway"}

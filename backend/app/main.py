from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def root():
    return {"message": "Local History Story Map API"}


@app.get("/health")
def health():
    return {"status": "ok"}

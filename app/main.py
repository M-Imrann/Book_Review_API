from routers import auth_router, book_router, review_router
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.database import Base, engine
import os


# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Book Review API", version="1.0.0")


# Include routers
app.include_router(auth_router.router)
app.include_router(book_router.router)
app.include_router(review_router.router)

# Mount static files for covers
UPLOAD_DIR = os.path.abspath("./uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/")
def read_root():
    return {"message": "Book Review API is running"}

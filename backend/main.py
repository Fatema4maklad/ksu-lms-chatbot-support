from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from rag_service import ask_lms_assistant
from routers import auth

app = FastAPI(title="KSU LMS Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "KSU LMS Chatbot API is running"}
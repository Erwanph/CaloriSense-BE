from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth, chat, user
from app.services.database_handler import DatabaseHandler

app = FastAPI(
    title="CaloriSense",
    version="1.0.0",
    description="A FastAPI backend for a mobile chatbot app using DeepSeek and Firebase."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DatabaseHandler.init()

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(user.router, prefix="/user", tags=["User"])

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Chatbot backend is running 🚀"}

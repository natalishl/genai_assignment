from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import List, Dict
from bot_app.bot_logic import get_answer
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load .env from root
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
env_path = os.path.join(project_root, ".env")
load_dotenv(dotenv_path=env_path)

app = FastAPI(title="Medical Bot API", description="API for medical chatbot", version="1.0.0")

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AskRequest(BaseModel):
    question: str
    chat_history: List[Dict[str, str]] = []

class AskResponse(BaseModel):
    answer: str
    chat_history: List[Dict[str, str]]
    error: str = None

@app.post("/ask", response_model=AskResponse)
async def ask_question(data: AskRequest):
    logger.info(f"Received question: {data.question}")
    try:
        question = data.question
        chat_history = data.chat_history

        response = get_answer(question, chat_history)

        logger.info("Response generated successfully.")
        return AskResponse(
            answer=response["answer"],
            chat_history=response["chat_history"]
        )

    except Exception as e:
        logger.error("Error while processing question", exc_info=True)
        return AskResponse(
            answer="מצטער, אירעה שגיאה בעיבוד השאלה. אנא נסה שוב.",
            chat_history=data.chat_history,
            error=str(e)
        )

@app.get("/health")
def health_check():
    logger.info("Health check requested.")
    return {"status": "healthy", "message": "✅ Bot API is running"}

@app.get("/")
def read_root():
    logger.info("Root endpoint called.")
    return {"message": "Medical Bot API", "docs": "/docs"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

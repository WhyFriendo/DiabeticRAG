from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import shutil
from rag import build_rag_system, answer_query

app = FastAPI(title="CareLink Data Assistant")

# Create data directory if it doesn't exist
os.makedirs("data", exist_ok=True)
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    answer: str

@app.get("/", response_class=HTMLResponse)
async def get_root():
    try:
        with open("templates/index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Error: index.html not found in templates directory.</h1>"

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")
    
    file_path = os.path.join("data", file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        build_rag_system(file_path)
        return {"message": "File uploaded and data processed successfully! You can now start chatting."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing CSV: {str(e)}")

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    try:
        answer = answer_query(req.query)
        return {"answer": answer}
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail="Please upload a CareLink CSV file first.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

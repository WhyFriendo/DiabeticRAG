from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import shutil
import csv
from dotenv import load_dotenv


load_dotenv()

from rag import build_rag_system, answer_query

def anonymize_csv(file_path: str):
    """Anonymizes sensitive data in the CareLink CSV file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)
            
        for i, row in enumerate(rows):
            # Anonymize row 1 (which follows the header on row 0)
            if i > 0 and len(rows[i-1]) >= 4 and "Last Name" in rows[i-1][0] and "First Name" in rows[i-1][1]:
                if len(row) >= 4:
                    row[0] = "Anonymous" # Last Name
                    row[1] = "Anonymous" # First Name
                    row[2] = ""          # Patient ID
                    row[3] = ""          # System ID
            
            # Anonymize Patient DOB row
            if len(row) >= 1 and row[0] == "Patient DOB":
                if len(row) > 1:
                    row[1] = "" # Clear DOB
                    
        with open(file_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(rows)
    except Exception as e:
        print(f"Failed to anonymize CSV: {e}")


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
        anonymize_csv(file_path)
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

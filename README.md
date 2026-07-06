# Diabetic RAG with CareLink data

RAG web application with user's continuous glucose monitoring (CGM) and insulin pump data exported from CareLink. Built with **FastAPI**, **LangChain**, and **OpenRouter**.

## Features

- **CSV Ingestion:** Upload raw CareLink CSV exports.
- **Auto-Anonymization:** The application automatically intercepts uploads and strips sensitive identifying information (Name, Patient ID, System ID, DOB) before the data is processed or embedded.
- **RAG Pipeline:** Utilizes LangChain and FAISS for fast local vector retrieval.
- **OpenRouter Integration:** Flexible LLM support (currently configured to use DeepSeek V4 Flash for chat and OpenAI for embeddings).
- **Dockerized:** Ready to deploy or run locally with docker.

## How to Run

### Option 1: Using Docker (Recommended)

1. Clone the repository and navigate into it:
   ```bash
   git clone https://github.com/WhyFriendo/DiabeticRAG.git
   cd DiabeticRAG
   ```
2. Create a `.env` file in the root directory and add your OpenRouter API key:
   ```env
   OPENROUTER_API_KEY="your_api_key_here"
   ```
3. Start the application:
   ```bash
   docker compose up
   ```
4. Open your browser and navigate to `http://localhost:8000`.

### Option 2: Using `uv` (Local Development)

1. Clone the repository.
2. Add your `.env` file with your `OPENROUTER_API_KEY`.
3. Start the server using `uv`:
   ```bash
   uv run uvicorn main:app --reload
   ```
4. Open your browser and navigate to `http://localhost:8000`.

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import chromadb
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
import os
from typing import List
import uuid
import io
import fitz  # PyMuPDF
from docx import Document
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize models and clients
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
chroma_client = chromadb.Client()
collection = chroma_client.create_collection(name="documents")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
gemini_model = genai.GenerativeModel('gemini-3.1-flash-lite-preview')

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Split text into overlapping chunks"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        start = end - overlap
    return chunks

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF"""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX"""
    doc = Document(io.BytesIO(file_bytes))
    return "\n".join([para.text for para in doc.paragraphs])

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload and process a document"""
    try:
        content = await file.read()
        
        # Extract text based on file type
        if file.filename.endswith('.pdf'):
            text = extract_text_from_pdf(content)
        elif file.filename.endswith('.docx'):
            text = extract_text_from_docx(content)
        elif file.filename.endswith('.txt'):
            text = content.decode('utf-8')
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")
        
        # Chunk the text
        chunks = chunk_text(text)
        
        # Generate embeddings and store in ChromaDB
        for i, chunk in enumerate(chunks):
            embedding = embedding_model.encode(chunk).tolist()
            collection.add(
                embeddings=[embedding],
                documents=[chunk],
                ids=[f"{file.filename}_{i}_{uuid.uuid4()}"]
            )
        
        return {"status": "success", "filename": file.filename, "chunks": len(chunks)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Handle chat requests with RAG"""
    try:
        # Generate query embedding
        query_embedding = embedding_model.encode(request.message).tolist()
        
        # Retrieve relevant chunks
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=3
        )
        
        # Build context from retrieved chunks
        context = "\n\n".join(results['documents'][0]) if results['documents'][0] else ""
        
        if not context:
            return ChatResponse(response="I could not find relevant information in the uploaded documents")
        
        # Create prompt with context
        prompt = f"""Context from uploaded documents:
{context}

User question: {request.message}

Please answer the question based only on the provided context. If the answer is not in the context, say "I could not find relevant information in the uploaded documents"."""
        
        # Call Gemini API
        response = gemini_model.generate_content(prompt)
        
        return ChatResponse(response=response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/clear")
async def clear_documents():
    """Clear all documents from the vector store"""
    global collection, chroma_client
    chroma_client.delete_collection(name="documents")
    collection = chroma_client.create_collection(name="documents")
    return {"status": "success"}

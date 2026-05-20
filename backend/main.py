from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
import cohere
from pinecone import Pinecone, ServerlessSpec
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
    allow_origins=["http://localhost:3000","https://abdullah-rag-bot.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize clients
cohere_client = cohere.Client(api_key=os.getenv("COHERE_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
gemini_model = genai.GenerativeModel('gemini-3.1-flash-lite-preview')

# Initialize or get Pinecone index
INDEX_NAME = "rag-documents"
DIMENSION = 1024  # Cohere embed-english-v3.0 dimension

# Create index if it doesn't exist
if INDEX_NAME not in pc.list_indexes().names():
    pc.create_index(
        name=INDEX_NAME,
        dimension=DIMENSION,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )

index = pc.Index(INDEX_NAME)

# Store for session management (in-memory, resets on server restart)
sessions = {}

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

class ChatResponse(BaseModel):
    response: str

class UploadRequest(BaseModel):
    session_id: str = "default"

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
async def upload_file(file: UploadFile = File(...), session_id: str = Form("default")):
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
        
        # Generate embeddings using Cohere
        response = cohere_client.embed(
            texts=chunks,
            model="embed-english-v3.0",
            input_type="search_document"
        )
        embeddings = response.embeddings
        
        # Prepare vectors for Pinecone with session namespace
        vectors = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            vector_id = f"{file.filename}_{i}_{uuid.uuid4()}"
            vectors.append({
                "id": vector_id,
                "values": embedding,
                "metadata": {
                    "text": chunk,
                    "filename": file.filename,
                    "chunk_index": i,
                    "session_id": session_id
                }
            })
        
        # Upsert to Pinecone with namespace
        index.upsert(vectors=vectors, namespace=session_id)
        
        # Track session
        if session_id not in sessions:
            sessions[session_id] = []
        sessions[session_id].append(file.filename)
        
        print(f"Uploaded {file.filename} to session {session_id} with {len(chunks)} chunks")
        
        return {"status": "success", "filename": file.filename, "chunks": len(chunks), "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Handle chat requests with RAG"""
    try:
        # Generate query embedding using Cohere
        response = cohere_client.embed(
            texts=[request.message],
            model="embed-english-v3.0",
            input_type="search_query"
        )
        query_embedding = response.embeddings[0]
        
        # Query Pinecone for relevant chunks in this session's namespace
        results = index.query(
            vector=query_embedding,
            top_k=3,
            include_metadata=True,
            namespace=request.session_id
        )
        
        print(f"Query in session {request.session_id}: found {len(results.matches)} matches")
        if results.matches:
            print(f"Best match score: {results.matches[0].score if results.matches else 0}")
        
        # Extract context from results
        context = "\n\n".join([match.metadata["text"] for match in results.matches if match.score > 0.3])
        
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
async def clear_documents(session_id: str = "default"):
    """Clear all documents from the vector store for this session"""
    try:
        # Delete all vectors in this namespace
        index.delete(delete_all=True, namespace=session_id)
        if session_id in sessions:
            del sessions[session_id]
        return {"status": "success", "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/session")
async def create_session():
    """Create a new session ID"""
    session_id = str(uuid.uuid4())
    return {"session_id": session_id}

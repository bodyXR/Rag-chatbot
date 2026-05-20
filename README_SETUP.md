# RAG Chatbot Setup Guide

## Prerequisites

- Node.js 18+ and npm
- Python 3.9+
- API Keys (all free tier):
  - Google Gemini API key: https://aistudio.google.com/apikey
  - Cohere API key: https://dashboard.cohere.com/api-keys
  - Pinecone API key: https://app.pinecone.io/

## Backend Setup

1. Navigate to the backend directory:

```bash
cd backend
```

2. Create a virtual environment:

```bash
python -m venv venv
```

3. Activate the virtual environment:

- Windows: `venv\Scripts\activate`
- Mac/Linux: `source venv/bin/activate`

4. Install dependencies:

```bash
pip install -r requirements.txt
```

5. Create a `.env` file with your API keys:

```bash
GEMINI_API_KEY=your_gemini_key
COHERE_API_KEY=your_cohere_key
PINECONE_API_KEY=your_pinecone_key
```

6. Start the FastAPI server:

```bash
uvicorn main:app --reload --port 8000
```

The backend will run on http://localhost:8000

## Frontend Setup

1. Install dependencies (from project root):

```bash
npm install
```

2. Start the development server:

```bash
npm run dev
```

The frontend will run on http://localhost:3000

## Usage

1. Open http://localhost:3000 in your browser
2. Upload PDF, TXT, or DOCX files using the sidebar
3. Wait for files to show "ready" status
4. Ask questions about your documents in the chat

## Features

- Drag and drop file upload
- Real-time processing status
- ChatGPT-style interface with dark theme
- Real-time processing status
- ChatGPT-style interface with dark theme
- Typing indicator during AI responses
- Cloud-based vector database (Pinecone)
- RAG-powered responses using Google Gemini 1.5 Flash
- Cohere embeddings for semantic search

# RAG Chatbot Setup Guide

## Prerequisites

- Node.js 18+ and npm
- Python 3.9+
- Google Gemini API key (free at https://makersuite.google.com/app/apikey)

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

5. Create a `.env` file with your Gemini API key:

```bash
GEMINI_API_KEY=your_api_key_here
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
- Typing indicator during AI responses
- In-memory vector database (no persistence)
- RAG-powered responses using Google Gemini 1.5 Flash (free tier)

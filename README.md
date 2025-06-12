# OnePaper: Academic Paper Analysis Platform

OnePaper is a full-stack web application designed to help users discover, analyze, and manage academic papers. It leverages AI to extract key information from papers and provides a semantic search and recommendation engine to find relevant research. The platform features a FastAPI backend, a Next.js frontend, and a suite of Python scripts for data processing.

## Architecture

The project is a monorepo containing three main components:

-   **`frontend/`**: A modern, responsive web interface built with Next.js, TypeScript, and Tailwind CSS.
-   **`backend/`**: A robust API server built with FastAPI that handles user authentication, data retrieval, and paper processing tasks.
-   **`processing/`**: A collection of Python scripts for batch processing of academic papers, including data extraction, cleaning, and embedding generation.

## Features

-   **User Authentication**: Secure user registration and login system using JWT for session management.
-   **Paper Submission**: Users can submit new papers from arXiv using their ID for asynchronous processing.
-   **AI-Powered Analysis**: Utilizes the ZhipuAI GLM-4-Flash model to extract structured data from papers, including:
    -   Main contribution
    -   Tasks, methods, and datasets
    -   Code links and key results
-   **Hybrid Search**: A powerful search engine combining traditional keyword matching with semantic vector search via ChromaDB for more relevant results. The system prioritizes matches in the title, then abstract, followed by semantic similarity.
-   **Semantic Recommendations**: Get suggestions for similar papers based on content embeddings.
-   **Personal Library**: Logged-in users can bookmark papers and manage them in a personal library.
-   **Filtering & Pagination**: Easily filter search results (e.g., for papers with code) and navigate through pages.

## Tech Stack

| Category              | Technology                                                                                                                                                             |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Frontend** | [Next.js](https://nextjs.org), [React](https://react.dev), [TypeScript](https://www.typescriptlang.org), [Tailwind CSS](https://tailwindcss.com), [shadcn/ui](https://ui.shadcn.com/), [Axios](https://axios-http.com/), [Zod](https://zod.dev) |
| **Backend** | [FastAPI](https://fastapi.tiangolo.com), [Python 3.11+](https://www.python.org), [SQLAlchemy](https://www.sqlalchemy.org), [Pydantic](https://pydantic.dev), [Passlib](https://passlib.readthedocs.io/en/stable/) |
| **Database** | [SQLite](https://www.sqlite.org) (for metadata), [ChromaDB](https://www.trychroma.com) (for vector storage)                                                                      |
| **AI & Data** | [Sentence-Transformers](https://www.sbert.net), [ZhipuAI](https://www.zhipuai.cn), [ArXiv API](https://info.arxiv.org/help/api/index.html), [PyMuPDF](https://pymupdf.readthedocs.io/en/latest/) |
| **Deployment** | [Fly.io](https://fly.io), [Uvicorn](https://www.uvicorn.org)                                                                                           |
| **Dev & Build Tools** | [Poetry](https://python-poetry.org), [NPM](https://www.npmjs.com)/[Yarn](https://yarnpkg.com)/[PNPM](https://pnpm.io), [ESLint](https://eslint.org), [Prettier](https://prettier.io/)     |

## Getting Started

Follow these instructions to get a local copy up and running.

### Prerequisites

-   Python 3.11+ and Poetry
-   Node.js and a package manager (npm, yarn, or pnpm)
-   ZhipuAI API Key

### Installation & Setup

1.  **Clone the Repository**
    ```bash
    git clone <repository-url>
    cd onepaper
    ```

2.  **Backend Setup**
    ```bash
    cd backend

    # Install dependencies
    poetry install

    # Create a .env file and add your secrets
    cp .env.example .env
    # Then edit .env with your JWT_SECRET_KEY and ZHIPU_API_KEY
    ```

3.  **Frontend Setup**
    ```bash
    cd ../frontend

    # Install dependencies
    npm install

    # Create a .env.local file for environment variables
    cp .env.local.example .env.local
    # Edit .env.local and set the backend API URL
    # NEXT_PUBLIC_API_URL=[http://127.0.0.1:8000](http://127.0.0.1:8000)
    ```

### Running the Application

1.  **Start the Backend Server**
    From the `backend/` directory:
    ```bash
    poetry run uvicorn src.backend.main:app --reload
    ```
    The API will be available at `http://127.0.0.1:8000`.

2.  **Start the Frontend Development Server**
    From the `frontend/` directory, open a new terminal:
    ```bash
    npm run dev
    ```
    Open [http://localhost:3000](http://localhost:3000) in your browser to see the application.

## Data Processing

The `processing/` directory contains scripts for populating the database. These are intended for initial data setup and batch processing, separate from the live application.

-   `download_pdfs.py`: Downloads PDF files from a source.
-   `process_meta.py` & `process_pdfs.py`: Scripts to run batch jobs on ZhipuAI to extract information from paper metadata and PDF text.
-   `generate_embeddings.py`: Generates embeddings for the processed papers and stores them in ChromaDB for semantic search.

import os
import arxiv
import sqlite3
import json
import chromadb
import traceback
from sentence_transformers import SentenceTransformer
from zhipuai import ZhipuAI

DB_FILE = "/app/data/papers.db"
CHROMA_DB_PATH = "/app/data/chroma_db"
COLLECTION_NAME = "papers"
MODEL_NAME = "all-MiniLM-L6-v2"
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")

PAGES_FROM_START = 15
PAGES_FROM_END = 10

print("[WORKER_INIT] Loading SentenceTransformer model...")
embedding_model = SentenceTransformer(MODEL_NAME)
print("[WORKER_INIT] Model loaded.")

print("[WORKER_INIT] Initializing ZhipuAI client...")
zhipu_client = ZhipuAI(api_key=ZHIPU_API_KEY)
print("[WORKER_INIT] ZhipuAI client initialized.")

arxiv_client = arxiv.Client()
print("[WORKER_INIT] Arxiv client initialized.")


def create_extraction_prompt(paper_text):
    return f"""You are an expert research assistant. Your task is to read the provided text from an academic paper and extract key information. The text may be truncated.

<document_text>
{paper_text}
</document_text>

Your response MUST be a single, valid JSON object. Do not include any text, explanations, or markdown formatting (like ```json) before or after the JSON object.

The JSON object must have the following keys: "title", "abstract", "contribution", "tasks", "methods", "datasets", "code_links", and "results".

- For "title" and "abstract", extract the exact title and abstract from the document.
- For "contribution", provide a one-sentence summary of the paper's main contribution.
- For "tasks", "methods", "datasets", and "code_links", provide a list of strings.
- For "results", provide a list of objects, where each object has "metric", "value", and "task" keys.
- If no information is found for a key, return an empty string "" or an empty list [].

Example output format:
{{
  "title": "The Title of the Paper Extracted from the Document",
  "abstract": "The full abstract text extracted directly from the document.",
  "contribution": "This paper introduces a novel attention mechanism that improves performance on translation tasks.",
  "tasks": ["Machine Translation", "GLUE Benchmark"],
  "methods": ["Novel Attention Mechanism", "Transformer"],
  "datasets": ["WMT 2014", "SQuAD"],
  "code_links": ["https://github.com/user/repo"],
  "results": [
    {{
      "metric": "BLEU Score",
      "value": "29.3",
      "task": "WMT 2014 En-De"
    }}
  ]
}}
"""


def extract_text_from_pdf(pdf_path):
    """
    Worker function that opens a PDF, extracts key text, and returns it.
    """
    try:
        import pymupdf

        filename = os.path.splitext(os.path.basename(pdf_path))[0]
        doc = pymupdf.open(pdf_path)

        text_parts = []
        total_pages = doc.page_count

        for i in range(min(total_pages, PAGES_FROM_START)):
            text_parts.append(doc.load_page(i).get_text("text"))

        text_parts.append("\n\n... [DOCUMENT TRUNCATED] ...\n\n")

        if total_pages > PAGES_FROM_START:
            start_page_for_end = max(PAGES_FROM_START, total_pages - PAGES_FROM_END)
            for i in range(start_page_for_end, total_pages):
                text_parts.append(doc.load_page(i).get_text("text"))

        doc.close()
        full_text = "".join(text_parts)
        return filename, full_text

    except Exception as e:
        print(f"Error processing PDF '{pdf_path}': {e}")
        return os.path.splitext(os.path.basename(pdf_path))[0], None


def process_new_paper(arxiv_id: str):
    """
    The main task function that the RQ worker will execute.
    Takes an arXiv ID, processes it, and saves it to the databases.
    """
    print(f"--- [WORKER] Starting processing for arXiv ID: {arxiv_id} ---")
    pdf_path = None

    try:
        print(f"[WORKER] Fetching data from arXiv...")
        search = arxiv.Search(id_list=[arxiv_id])
        paper = next(arxiv_client.results(search))

        temp_dir = "./temp_pdfs"
        os.makedirs(temp_dir, exist_ok=True)
        pdf_path = paper.download_pdf(dirpath=temp_dir, filename=f"{arxiv_id}.pdf")
        print(f"[WORKER] PDF downloaded to: {pdf_path}")

        _, full_text = extract_text_from_pdf(pdf_path)
        if not full_text:
            raise ValueError(f"Failed to extract text from PDF for {arxiv_id}")

        print(f"[WORKER] Calling LLM for data extraction...")
        prompt = create_extraction_prompt(full_text)
        response = zhipu_client.chat.completions.create(
            model="glm-4-flash",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )

        content_str = response.choices[0].message.content
        extracted_info = json.loads(content_str)
        print(f"[WORKER] LLM extraction successful.")

        print(f"[WORKER] Generating embedding...")
        text_to_embed = f"{extracted_info.get('title', '')}. {extracted_info.get('abstract', '')}"
        embedding = embedding_model.encode(text_to_embed)

        print(f"[WORKER] Saving to SQLite...")
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        paper_id_db = arxiv_id
        cursor.execute(
            """
            INSERT INTO papers (
                id, title, abstract, authors, contribution, tasks, methods, datasets, code_links, results, processed
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE
            SET title = excluded.title, abstract = excluded.abstract, authors = excluded.authors, contribution = excluded.contribution, tasks = excluded.tasks, methods = excluded.methods, datasets = excluded.datasets, code_links = excluded.code_links, results = excluded.results, processed = excluded.processed
            """,
            (
                paper_id_db,
                extracted_info.get('title'),
                extracted_info.get('abstract'),
                ','.join([str(a) for a in paper.authors]),
                extracted_info.get('contribution'),
                json.dumps(extracted_info.get('tasks', [])),
                json.dumps(extracted_info.get('methods', [])),
                json.dumps(extracted_info.get('datasets', [])),
                json.dumps(extracted_info.get('code_links', [])),
                json.dumps(extracted_info.get('results', [])),
                2
            )
        )
        conn.commit()
        conn.close()

        print(f"[WORKER] Saving to ChromaDB...")
        chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        paper_collection = chroma_client.get_or_create_collection(name=COLLECTION_NAME)
        paper_collection.upsert(
            ids=[paper_id_db],
            embeddings=[embedding.tolist()]
        )

        print(f"--- [WORKER] Successfully processed and saved arXiv ID: {arxiv_id} ---")
        return f"Success: {arxiv_id}"

    except Exception as e:
        print(f"--- [WORKER] FAILED to process arXiv ID: {arxiv_id} ---")
        print(traceback.format_exc())
        return f"Failed: {e}"
    finally:
        if pdf_path and os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
                print(f"[WORKER] Cleaned up temporary file: {pdf_path}")
            except OSError as e:
                print(f"[WORKER] Error cleaning up file {pdf_path}: {e}")

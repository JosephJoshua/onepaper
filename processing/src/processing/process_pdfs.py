import os
import json
import sqlite3
import time
import pymupdf
import multiprocessing
from tqdm import tqdm
from zhipuai import ZhipuAI
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")
PDF_DIRECTORY = "_data/pdfs"
DB_FILE = "_data/papers.db"

# Base names for batch files; sequence numbers will be appended
BATCH_INPUT_FILE_PDFS_BASE = "_data/batch_input_pdfs"
BATCH_OUTPUT_FILE_PDFS_BASE = "_data/batch_output_pdfs"

PDF_PROCESS_LIMIT = 2000
MAX_BATCH_FILE_SIZE_MB = 45
MAX_BATCH_FILE_SIZE_BYTES = MAX_BATCH_FILE_SIZE_MB * 1024 * 1024

PAGES_FROM_START = 15
PAGES_FROM_END = 10

def extract_text_from_pdf(pdf_path):
    """
    Worker function that opens a PDF, extracts key text, and returns it.
    Designed to be run in a separate process.
    """
    try:
        filename = os.path.splitext(os.path.basename(pdf_path))[0]
        doc = pymupdf.open(pdf_path)

        text_parts = []
        total_pages = doc.page_count

        # Extract text from the first few pages
        for i in range(min(total_pages, PAGES_FROM_START)):
            text_parts.append(doc.load_page(i).get_text("text"))

        text_parts.append("\n\n... [DOCUMENT TRUNCATED] ...\n\n")

        # Extract text from the last few pages (if the document is long enough)
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


def create_extraction_prompt(paper_text):
    """
    Creates a highly structured prompt using the extracted PDF text.
    Requests a clean JSON object for the output.
    """
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


def prepare_pdf_batch_files():
    """
    Uses a multiprocessing pool to parse PDFs and create batch input files,
    splitting them if they exceed MAX_BATCH_FILE_SIZE_BYTES.
    Returns a list of created batch input file paths.
    """
    print(f"Scanning for PDFs in '{PDF_DIRECTORY}'...")
    all_pdf_files = [os.path.join(PDF_DIRECTORY, f) for f in os.listdir(PDF_DIRECTORY) if f.endswith(".pdf")]

    if PDF_PROCESS_LIMIT and PDF_PROCESS_LIMIT > 0:
        all_pdf_files = all_pdf_files[:PDF_PROCESS_LIMIT]

    if not all_pdf_files:
        print("No PDFs found to process.")
        return []

    print(f"Found {len(all_pdf_files)} PDFs to process.")

    created_batch_files = []
    current_batch_file_number = 1
    current_batch_file_path = f"{BATCH_INPUT_FILE_PDFS_BASE}_{current_batch_file_number}.jsonl"
    current_batch_file_size = 0
    outfile = None

    # Use all available CPU cores
    with multiprocessing.Pool() as pool:
        results_iterator = pool.imap_unordered(extract_text_from_pdf, all_pdf_files)

        print("Starting parallel PDF text extraction and batch file preparation...")
        for paper_id, text in tqdm(results_iterator, total=len(all_pdf_files), desc="Extracting PDF Text & Building Batches"):
            if text:
                prompt_text = create_extraction_prompt(text)
                batch_request = {
                    "custom_id": paper_id,
                    "method": "POST",
                    "url": "/v4/chat/completions",
                    "body": {
                        "model": "glm-4-flash",
                        "messages": [{"role": "user", "content": prompt_text}],
                        "response_format": {"type": "json_object"},
                        "stream": False,
                        "temperature": 0.0,
                    }
                }
                request_line = json.dumps(batch_request) + '\n'
                request_line_size = len(request_line.encode('utf-8'))

                if outfile is None: # First entry or new batch file
                    outfile = open(current_batch_file_path, 'w', encoding='utf-8')
                    print(f"Creating batch file: {current_batch_file_path}")

                # Check if adding this request exceeds the max file size
                if current_batch_file_size > 0 and (current_batch_file_size + request_line_size > MAX_BATCH_FILE_SIZE_BYTES):
                    outfile.close()
                    created_batch_files.append(current_batch_file_path)
                    print(f"Completed batch file: {current_batch_file_path} (Size: {current_batch_file_size / (1024*1024):.2f} MB)")

                    current_batch_file_number += 1
                    current_batch_file_path = f"{BATCH_INPUT_FILE_PDFS_BASE}_{current_batch_file_number}.jsonl"
                    outfile = open(current_batch_file_path, 'w', encoding='utf-8')
                    print(f"Creating new batch file: {current_batch_file_path}")
                    current_batch_file_size = 0

                outfile.write(request_line)
                current_batch_file_size += request_line_size

    if outfile: # Close the last opened file
        outfile.close()
        created_batch_files.append(current_batch_file_path)
        print(f"Completed batch file: {current_batch_file_path} (Size: {current_batch_file_size / (1024*1024):.2f} MB)")


    if not created_batch_files:
        print("No batch files were created (perhaps no PDFs processed successfully).")
    else:
        print(f"Finished preparing {len(created_batch_files)} batch file(s) for PDFs.")
    return created_batch_files


def process_batch_results_pdf(batch_output_file_path):
    """Reads a specific batch output file, parses the JSON, and UPDATES the ease."""
    print(f"Processing PDF results from '{batch_output_file_path}'...")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    processed_count = 0

    try:
        with open(batch_output_file_path, 'r', encoding='utf-8') as f:
            for line in tqdm(f, desc=f"Updating DB from {os.path.basename(batch_output_file_path)}"):
                try:
                    result_data = json.loads(line)
                    paper_id = result_data.get('custom_id')

                    response_body = result_data.get('response', {}).get('body', {})
                    choices = response_body.get('choices')
                    if not choices or not isinstance(choices, list) or len(choices) == 0:
                        print(f"Warning: No 'choices' in response for paper {paper_id}. Skipping.")
                        continue

                    message = choices[0].get('message', {})
                    content_str = message.get('content', '{}')

                    if not content_str or content_str == '{}':
                         print(f"Warning: Empty 'content' in response for paper {paper_id}. Skipping.")
                         continue

                    extracted_info = json.loads(content_str)

                    title = extracted_info.get('title', '').strip()
                    abstract = extracted_info.get('abstract', '').strip()

                    contribution = extracted_info.get('contribution', '')
                    tasks = json.dumps(extracted_info.get('tasks', []))
                    methods = json.dumps(extracted_info.get('methods', []))
                    datasets = json.dumps(extracted_info.get('datasets', []))
                    code_links = json.dumps(extracted_info.get('code_links', []))
                    results = json.dumps(extracted_info.get('results', []))

                    cursor.execute(
                        """
                        INSERT INTO papers (
                            id, title, abstract, contribution, tasks, methods, datasets, code_links, results, processed
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(id) DO UPDATE
                        SET title = excluded.title, abstract = excluded.abstract, contribution = excluded.contribution, tasks = excluded.tasks, methods = excluded.methods, datasets = excluded.datasets, code_links = excluded.code_links, results = excluded.results, processed = excluded.processed""",
                        (paper_id, title, abstract, contribution, tasks, methods, datasets, code_links, results, 2)
                    )

                    processed_count +=1
                except json.JSONDecodeError as e:
                    print(f"Warning: Could not parse JSON content for paper {paper_id}. Error: {e}. Content: '{content_str[:200]}...'")
                    continue
                except (IndexError, KeyError, AttributeError) as e: # Added AttributeError
                    print(f"Warning: Could not process result structure for paper {paper_id}. Error: {e}. Result data: {result_data}")
                    continue
    except FileNotFoundError:
        print(f"Error: Output file '{batch_output_file_path}' not found.")
        conn.close()
        return

    conn.commit()
    conn.close()
    print(f"Database has been updated with {processed_count} richly extracted PDF information from '{batch_output_file_path}'.")


def main():
    if ZHIPU_API_KEY == "YOUR_ZHIPU_API_KEY" or not ZHIPU_API_KEY:
        print("Error: Please set your ZHIPU_API_KEY in the script.")
        return

    client = ZhipuAI(api_key=ZHIPU_API_KEY)

    # batch_input_files = prepare_pdf_batch_files()
    batch_input_files = []
    batch_output_files = ['_data/batch_output_pdfs_1.jsonl', '_data/batch_output_pdfs_2.jsonl', '_data/batch_output_pdfs_3.jsonl']  # Placeholder for output files

    for file in batch_output_files:
        process_batch_results_pdf(file)

    return

    if not batch_input_files:
        print("No batch input files created. Exiting.")
        return

    for i, batch_input_file_path in enumerate(tqdm(batch_input_files, desc="Processing Batches")):
        batch_number = i + 1
        print(f"\n--- Processing Batch {batch_number}/{len(batch_input_files)}: {batch_input_file_path} ---")

        current_batch_output_file = f"{BATCH_OUTPUT_FILE_PDFS_BASE}_{batch_number}.jsonl"

        print(f"Performing sanity check on '{batch_input_file_path}'...")
        if not os.path.exists(batch_input_file_path) or os.path.getsize(batch_input_file_path) == 0:
            print(f"Error: The batch input file '{batch_input_file_path}' is empty or was not created. Skipping this batch.")
            continue
        print("Sanity check passed.")

        print(f"Uploading '{batch_input_file_path}' to Zhipu AI...")
        try:
            with open(batch_input_file_path, "rb") as f:
                batch_file_obj = client.files.create(file=f, purpose="batch")
            print(f"File uploaded successfully. File ID: {batch_file_obj.id}")
        except Exception as e:
            print(f"Error uploading file '{batch_input_file_path}': {e}")
            continue # Skip to next batch

        print(f"Creating batch job for File ID: {batch_file_obj.id}...")
        try:
            batch_job = client.batches.create(
                input_file_id=batch_file_obj.id,
                endpoint="/v4/chat/completions",
                completion_window="24h"
            )
            print(f"Batch job created successfully. Job ID: {batch_job.id}")
        except Exception as e:
            print(f"Error creating batch job for '{batch_input_file_path}': {e}")
            continue # Skip to next batch

        print(f"Monitoring job {batch_job.id} status... (This can take a long time)")
        job_status = None
        while True:
            try:
                job_status = client.batches.retrieve(batch_job.id)
                status_line = f"Job {batch_job.id} status: {job_status.status}"
                if job_status.in_progress_at:
                    status_line += f" | In-progress: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(job_status.in_progress_at))}"
                if job_status.completed_at:
                     status_line += f" | Completed: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(job_status.completed_at))}"
                print(status_line)

                if job_status.status in ['completed', 'failed', 'cancelled']:
                    break
                time.sleep(60) # Check every 60 seconds
            except Exception as e:
                print(f"Error retrieving job status for {batch_job.id}: {e}. Retrying in 60s.")
                time.sleep(60)

        if job_status and job_status.status == 'completed':
            print(f"Job {batch_job.id} completed. Retrieving results...")
            try:
                result_file_id = job_status.output_file_id
                if not result_file_id:
                    print(f"Error: Job {batch_job.id} completed but no output_file_id found.")
                    continue

                result_content = client.files.content(result_file_id).content
                with open(current_batch_output_file, 'wb') as f:
                    f.write(result_content)
                print(f"Results for job {batch_job.id} saved to '{current_batch_output_file}'.")
                process_batch_results_pdf(current_batch_output_file)
            except Exception as e:
                print(f"Error retrieving or saving results for job {batch_job.id}: {e}")
        elif job_status:
            print(f"Job {batch_job.id} finished with status: {job_status.status}. No results to process for this batch.")
            if job_status.error_file_id:
                try:
                    error_content_response = client.files.content(job_status.error_file_id)
                    # Similar handling for error content as for result content
                    if hasattr(error_content_response, 'text'):
                        error_details = error_content_response.text
                    elif hasattr(error_content_response, 'content'):
                         error_details = error_content_response.content.decode('utf-8', errors='ignore')
                    else:
                        error_details = str(error_content_response) # Convert raw response to string

                    print(f"Error file ID for job {batch_job.id}: {job_status.error_file_id}. Content (first 500 chars): {error_details[:500]}")

                    error_file_path = f"{BATCH_OUTPUT_FILE_PDFS_BASE}_{batch_number}_error.jsonl"
                    with open(error_file_path, 'w', encoding='utf-8') as ef:
                       ef.write(error_details)

                    print(f"Error details saved to {error_file_path}")
                except Exception as e_file:
                    print(f"Could not retrieve or parse error file content for {job_status.error_file_id}: {e_file}")
            else:
                 print(f"Job {batch_job.id} status: {job_status.status}, and no error file ID provided.")

        else:
            print(f"Job {batch_job.id} status could not be determined. Skipping.")

        print(f"--- Finished Batch {batch_number}/{len(batch_input_files)} ---")

    print("\nAll PDF processing batches complete.")


if __name__ == "__main__":
    main()
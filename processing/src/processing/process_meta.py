import os
import json
import sqlite3
import time
from zhipuai import ZhipuAI
from tqdm import tqdm

# --- Configuration ---
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")
META_JSONL_FILE = "_data/meta/arxiv.jsonl"
DB_FILE = "_data/papers.db"
BATCH_INPUT_FILE = "_data/batch_input_final.jsonl"
BATCH_OUTPUT_FILE = "_data/batch_output_final.jsonl"

# --- Database Setup ---
def setup_database():
    """Creates the SQLite database with a detailed table schema."""
    print(f"Setting up database at '{DB_FILE}'...")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS papers (
            id TEXT PRIMARY KEY,
            title TEXT,
            authors TEXT,
            abstract TEXT,
            contribution TEXT,
            tasks TEXT,
            methods TEXT,
            datasets TEXT,
            code_links TEXT,
            results TEXT,
            processed INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()
    print("Database setup complete.")


def create_extraction_prompt(title, abstract):
    """
    Creates a highly structured prompt using XML for input clarity
    and requests a clean JSON object for the output.
    """
    return f"""
You are an expert research assistant. Your task is to analyze the title and abstract of the academic paper provided below inside the `<paper>` tags and extract key information.

<paper>
  <title>{title}</title>
  <abstract>{abstract}</abstract>
</paper>

Your response MUST be a single, valid JSON object. Do not include any text, explanations, or markdown formatting (like ```json) before or after the JSON object.

The JSON object must have the following keys: "contribution", "tasks", "methods", "datasets", "code_links", and "results".

- For "contribution", provide a one-sentence summary of the paper's main contribution.
- For "tasks", "methods", "datasets", and "code_links", provide a list of strings.
- For "results", provide a list of objects, where each object has "metric", "value", and "task" keys.
- If no information is found for a key, return an empty string "" for "contribution" or an empty list [] for the others.

Here is an example of the required output format:
{{
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


# --- Batch Job Preparation ---
def prepare_batch_file_and_db(limit=10000):
    """
    Parses the meta JSONL, populates the DB, and creates the batch input file.
    """
    print(f"Preparing batch input file '{BATCH_INPUT_FILE}' and populating database...")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    with open(META_JSONL_FILE, 'r', encoding='utf-8') as infile, \
            open(BATCH_INPUT_FILE, 'w', encoding='utf-8') as outfile:

        for i, line in enumerate(tqdm(infile, desc="Processing metadata", total=limit)):
            if i >= limit:
                break
            try:
                line = line.rstrip(',')

                paper_data = json.loads(line)
                paper_id = paper_data.get('_id')
                title = paper_data.get('title', '').strip().replace("\n", " ")
                abstract = paper_data.get('abstract', '').strip().replace("\n", " ")

                if not paper_id or not title or not abstract:
                    continue

                cursor.execute(
                    "INSERT OR IGNORE INTO papers (id, title, authors, abstract) VALUES (?, ?, ?, ?)",
                    (paper_id, title, json.dumps(paper_data.get('author')), abstract)
                )

                prompt_text = create_extraction_prompt(title, abstract)

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
                    },
                }

                outfile.write(json.dumps(batch_request) + '\n')

            except json.JSONDecodeError as e:
                print(f"Warning: Skipping malformed JSON on line {i + 1}: {e}")
                continue

    conn.commit()
    conn.close()
    print(f"Finished preparing. {limit} papers ready for batch processing.")


# --- Result Processing ---
def process_batch_results():
    """Reads the batch output file, parses the JSON, and updates the database."""
    print(f"Processing results from '{BATCH_OUTPUT_FILE}'...")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        with open(BATCH_OUTPUT_FILE, 'r', encoding='utf-8') as f:
            for line in tqdm(f, desc="Updating database with JSON results"):
                try:
                    result_data = json.loads(line)
                    paper_id = result_data.get('custom_id')

                    print(paper_id)

                    response_body = result_data.get('response', {}).get('body', {})
                    content_str = response_body.get('choices', [{}])[0].get('message', {}).get('content', '{}')

                    # The LLM output is a JSON string, so we parse it directly.
                    extracted_info = json.loads(content_str)

                    contribution = extracted_info.get('contribution', '')
                    tasks = json.dumps(extracted_info.get('tasks', []))
                    methods = json.dumps(extracted_info.get('methods', []))
                    datasets = json.dumps(extracted_info.get('datasets', []))
                    code_links = json.dumps(extracted_info.get('code_links', []))
                    results = json.dumps(extracted_info.get('results', []))

                    cursor.execute(
                        """
                        UPDATE papers 
                        SET contribution = ?, tasks = ?, methods = ?, datasets = ?, 
                            code_links = ?, results = ?, processed = 1
                        WHERE id = ?
                        """,
                        (contribution, tasks, methods, datasets, code_links, results, paper_id)
                    )

                except (json.JSONDecodeError, IndexError, KeyError) as e:
                    print(f"Warning: Could not process result for paper {paper_id}. Error: {e}")
                    continue
    except FileNotFoundError:
        print(f"Error: Output file '{BATCH_OUTPUT_FILE}' not found.")
        return

    conn.commit()
    conn.close()
    print("Database has been updated with JSON-extracted information.")


def main():
    if ZHIPU_API_KEY == "YOUR_ZHIPU_API_KEY":
        print("Error: Please replace 'YOUR_ZHIPU_API_KEY' in the script.")
        return

    client = ZhipuAI(api_key=ZHIPU_API_KEY)

    setup_database()
    prepare_batch_file_and_db(limit=10000)

    print(f"Uploading '{BATCH_INPUT_FILE}' to Zhipu AI...")
    try:
        f = open(BATCH_INPUT_FILE, 'rb')
        batch_file = client.files.create(file=f, purpose="batch")
        print(f"File uploaded successfully. File ID: {batch_file.id}")
    except Exception as e:
        print(f"Error uploading file: {e}")
        return

    print("Creating batch job...")
    try:
        batch_job = client.batches.create(
            input_file_id=batch_file.id,
            endpoint="/v4/chat/completions",
            completion_window="24h"
        )

        print(f"Batch job created successfully. Job ID: {batch_job.id}")
    except Exception as e:
        print(f"Error creating batch job: {e}")
        return

    print("Monitoring job status... (This can take a long time)")
    while True:
        try:
            job_status = client.batches.retrieve(batch_job.id)
            print(
                f"Current job status: {job_status.status} | In-progress: {job_status.in_progress_at} | Completed: {job_status.completed_at}")
            if job_status.status in ['completed', 'failed', 'cancelled']:
                break
            time.sleep(60)
        except Exception as e:
            print(f"Error retrieving job status: {e}")
            time.sleep(60)

    if job_status.status == 'completed':
        print("Job completed. Retrieving results...")
        try:
            result_file_id = job_status.output_file_id
            result_content = client.files.content(result_file_id).content
            with open(BATCH_OUTPUT_FILE, 'wb') as f:
                f.write(result_content)
            print(f"Results saved to '{BATCH_OUTPUT_FILE}'.")
            process_batch_results()
        except Exception as e:
            print(f"Error retrieving results: {e}")
    else:
        print(f"Job finished with status: {job_status.status}. No results to process.")
        if job_status.error_file_id:
            print(f"Check the error file with ID: {job_status.error_file_id}")


if __name__ == "__main__":
    main()
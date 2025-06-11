import json
from tqdm import tqdm

# --- Configuration ---
INPUT_JSON_FILE = 'meta/arxiv.json'
OUTPUT_JSONL_FILE = 'meta/arxiv.jsonl'


def convert_json_to_jsonl(input_path, output_path):
    """
    Reads a file containing a single JSON array and converts it to
    a JSON Lines file where each object is on a new line.
    """
    print(f"Opening '{input_path}'...")
    try:
        with open(input_path, 'r', encoding='utf-8') as infile:
            contents = '[' + infile.read().rstrip().rstrip(',') + ']'
            data = json.loads(contents)

            if not isinstance(data, list):
                print("Error: The input file is not a JSON array (a list of objects).")
                return

            print(f"Found {len(data)} objects. Converting to JSONL format...")

            with open(output_path, 'w', encoding='utf-8') as outfile:
                for entry in tqdm(data, desc="Writing to .jsonl"):
                    outfile.write(json.dumps(entry) + '\n')

            print(f"Successfully converted file to '{output_path}'")

    except FileNotFoundError:
        print(f"Error: The file '{input_path}' was not found. Please check the path.")
    except json.JSONDecodeError as e:
        print(f"Error: The file '{input_path}' is not a valid JSON file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    convert_json_to_jsonl(INPUT_JSON_FILE, OUTPUT_JSONL_FILE)

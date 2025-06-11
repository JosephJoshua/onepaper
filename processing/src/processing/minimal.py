import os
from zhipuai import ZhipuAI

# --- Configuration ---
# 1. Paste your Zhipu AI API Key here
ZHIPU_API_KEY = "bc68ca1b24e74c56afdf8ff7457e3b49.ZjZ5VQeHgFo7c5f6"

# 2. We will create a dummy file for the test
TEST_FILE_NAME = "minimal_batch_input.jsonl"


# --- End Configuration ---

def create_dummy_file():
    """Creates a small, valid .jsonl file with one line."""
    print(f"Creating a dummy file named '{TEST_FILE_NAME}'...")
    dummy_content = {
        "custom_id": "test-001",
        "method": "POST",
        "url": "/v4/chat/completions",
        "body": {
            "model": "glm-4-flash",
            "messages": [
                {"role": "user", "content": "What is the capital of France?"}
            ],
            "temperature": "0.0"
        }
    }
    with open(TEST_FILE_NAME, 'w', encoding='utf-8') as f:
        f.write(str(dummy_content).replace("'", '"') + '\n')  # Simple way to write a JSON line
    print("Dummy file created successfully.")


def run_minimal_upload_test():
    """
    Tests only the file upload functionality with the ZhipuAI SDK.
    """
    if ZHIPU_API_KEY == "YOUR_ZHIPU_API_KEY":
        print("Error: Please replace 'YOUR_ZHIPU_API_KEY' in the script.")
        return

    # Create the file we are going to upload
    create_dummy_file()

    print("\nInitializing ZhipuAI client...")
    client = ZhipuAI(api_key=ZHIPU_API_KEY)

    print(f"Attempting to upload '{TEST_FILE_NAME}'...")
    try:
        # The actual API call we are testing
        response = client.files.create(
            file=open(TEST_FILE_NAME, "rb"),
            purpose="batch"
        )

        # If we get here, it worked!
        print("\n--- SUCCESS! ---")
        print("File uploaded successfully.")
        print(f"Response ID: {response.id}")
        print(f"Filename: {response.filename}")
        print(f"Purpose: {response.purpose}")
        print(f"Status: {response.status}")

    except Exception as e:
        print("\n--- FAILURE! ---")
        print(f"The upload failed with an error: {e}")

    finally:
        # Clean up the dummy file
        if os.path.exists(TEST_FILE_NAME):
            os.remove(TEST_FILE_NAME)
            print(f"\nCleaned up dummy file '{TEST_FILE_NAME}'.")


if __name__ == "__main__":
    run_minimal_upload_test()
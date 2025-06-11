import sqlite3
import chromadb
import numpy as np
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

DB_FILE = "_data/papers.db"
CHROMA_DB_PATH = "../backend/chroma_db"
COLLECTION_NAME = "papers"
MODEL_NAME = 'all-MiniLM-L6-v2'

BATCH_SIZE = 32

def main():
    """
    Reads paper data from SQLite, generates embeddings, and upserts them into ChromaDB.
    """
    print("Initializing model and database connections...")

    model = SentenceTransformer(MODEL_NAME)
    print(f"SentenceTransformer model '{MODEL_NAME}' loaded.")

    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )
    print(f"ChromaDB collection '{COLLECTION_NAME}' ready.")

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT id, title, abstract FROM papers WHERE title IS NOT NULL AND abstract IS NOT NULL")
    all_papers = cursor.fetchall()
    conn.close()

    if not all_papers:
        print("No papers found in the SQLite database. Exiting.")
        return

    print(f"Found {len(all_papers)} papers to process.")

    valid_count = 0
    failed_count = 0

    for i in tqdm(range(0, len(all_papers), BATCH_SIZE), desc="Generating and Storing Embeddings"):
        batch = all_papers[i:i + BATCH_SIZE]
        paper_ids = [row['id'] for row in batch]

        texts_to_embed = [f"{row['title']}. {row['abstract']}" for row in batch]

        id_to_search = '63bcd73090e50fcafdef9941'
        if id_to_search in paper_ids:
            index = paper_ids.index(id_to_search)
            print(f"Text to embed for ID {id_to_search}: {texts_to_embed[index]}")

        embeddings = model.encode(texts_to_embed, show_progress_bar=False)

        if id_to_search in paper_ids:
            index = paper_ids.index(id_to_search)
            print(f"Embedding for ID {id_to_search}: {embeddings[index]}")

        valid_ids = []
        valid_embeddings = []

        for j, embedding in enumerate(embeddings):
            if embedding is not None and hasattr(embedding, 'tolist'):
                valid_ids.append(str(batch[j]['id']).strip())
                valid_embeddings.append(embedding)
            else:
                # Log the problematic paper ID
                failed_id = str(batch[j]['id']).strip()
                print(f"Warning: Failed to generate a valid embedding for paper ID: {failed_id}. Skipping.")

        if valid_ids:
            valid_count += len(valid_ids)

            collection.upsert(
                ids=valid_ids,
                embeddings=valid_embeddings
            )

        test_id = valid_ids[0]
        try:
            retrieved = collection.get(ids=[test_id], include=["embeddings"])

            verification_passed = True
            if not retrieved or not retrieved.get('ids'):
                verification_passed = False
                print(f"\n--- VERIFICATION FAILED! ---")
                print(f"ID '{test_id}' could not be found after upsert.")
            else:
                retrieved_embedding = retrieved['embeddings'][0]
                if retrieved_embedding is None or not isinstance(retrieved_embedding, (list, np.ndarray)):
                    verification_passed = False
                    print(f"\n--- VERIFICATION FAILED! ---")
                    print(f"ID '{test_id}' was found, but its embedding is NULL or not a valid array/list.")
                    print(f"Retrieved object: {retrieved}")

            if verification_passed:
                if i == 0:  # Print only for the first batch
                    print(f"\n--- VERIFICATION SUCCEEDED for batch 1! ---")
                    print(f"Successfully retrieved a valid embedding for ID '{test_id}'.")
                    print("This confirms data is being stored and retrieved correctly.")
                    print("--------------------------------------------\n")
            else:
                failed_count += 1
        except Exception as e:
            print(f"\nFATAL ERROR during verification get(): {e}")

    print("\nEmbedding generation complete!")
    print(f"Total items in collection '{COLLECTION_NAME}': {collection.count()}")
    print(f"Inserted {valid_count} papers into the collection.")
    print(f"Failed to generate embeddings for {failed_count} papers.")


if __name__ == "__main__":
    main()

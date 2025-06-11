import sqlite3
import chromadb
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

DB_FILE = "_data/papers.db"
CHROMA_DB_PATH = "_data/chroma_db"
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

    for i in tqdm(range(0, len(all_papers), BATCH_SIZE), desc="Generating and Storing Embeddings"):
        batch = all_papers[i:i + BATCH_SIZE]
        paper_ids = [row['id'] for row in batch]

        texts_to_embed = [f"{row['title']}. {row['abstract']}" for row in batch]

        embeddings = model.encode(texts_to_embed, show_progress_bar=False).tolist()

        collection.upsert(
            ids=paper_ids,
            embeddings=embeddings,
        )

    print("\nEmbedding generation complete!")
    print(f"Total items in collection '{COLLECTION_NAME}': {collection.count()}")


if __name__ == "__main__":
    main()

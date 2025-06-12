import os
from typing import List, Optional
from datetime import timedelta

import redis
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from rq import Queue
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware

from . import auth, models, schemas, database, tasks

import chromadb
from sentence_transformers import SentenceTransformer

models.Base.metadata.create_all(bind=database.engine)

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
chroma_client = chromadb.PersistentClient(path="/app/data/chroma_db")
paper_collection = chroma_client.get_collection(name="papers")

redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
conn = redis.from_url(redis_url)
q = Queue(connection=conn)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Authentication Endpoints ---
@app.post("/token", response_model=schemas.Token)
def login_for_access_token(
    db: Session = Depends(database.get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    user = auth.get_user(db, email=form_data.username)  # username is the email
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/users/register", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    db_user = auth.get_user(db, email=str(user.email))
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = auth.get_password_hash(user.password)

    db_user = models.User(
        email=str(user.email), name=user.name, hashed_password=hashed_password
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


@app.get("/users/me", response_model=schemas.User)
def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user


# --- Paper Endpoints ---
@app.post("/papers/submit", status_code=status.HTTP_202_ACCEPTED)
def submit_paper_for_processing(
        submission: schemas.ArxivSubmission,
        db: Session = Depends(database.get_db),
        current_user: models.User = Depends(auth.get_current_user),
):
    existing_paper = db.query(models.Paper).filter(models.Paper.id == submission.arxiv_id).first()
    if existing_paper and getattr(existing_paper, 'processed', 0) == 2:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Paper with arXiv ID {submission.arxiv_id} has already been fully processed."
        )

    job = q.enqueue(tasks.process_new_paper, submission.arxiv_id, job_timeout='10m')

    return {"message": "Paper submission accepted for processing.", "job_id": job.id}

@app.get("/papers", response_model=schemas.PaginatedPaperResponse)
def read_papers(
    db: Session = Depends(database.get_db),
    page: int = 1,
    per_page: int = 12,
    search: Optional[str] = None,
    has_code: Optional[bool] = None,
):
    if search:
        print(f"Performing semantic search for: '{search}'")

        query_embedding = embedding_model.encode(search).tolist()

        results = paper_collection.query(
            query_embeddings=[query_embedding],
            n_results=200,
        )

        similar_ids = results["ids"][0]
        if not similar_ids:
            # If no semantic matches, return empty
            return {
                "total_items": 0,
                "total_pages": 0,
                "page": 1,
                "per_page": per_page,
                "items": [],
            }

        from sqlalchemy import case

        ordering = case(
            {id: i for i, id in enumerate(similar_ids)}, value=models.Paper.id
        )
        query = (
            db.query(models.Paper)
            .filter(models.Paper.id.in_(similar_ids))
            .order_by(ordering)
        )

    else:
        query = db.query(models.Paper).order_by(models.Paper.title.desc())

    if has_code is not None:
        if has_code:
            query = query.filter(models.Paper.code_links.isnot(None)).filter(
                models.Paper.code_links != "[]"
            )
        else:
            query = query.filter(
                (models.Paper.code_links.is_(None)) | (models.Paper.code_links == "[]")
            )

    total_items = query.count()
    offset = (page - 1) * per_page
    papers = query.offset(offset).limit(per_page).all()

    parsed_papers = [
        schemas.PaperBase(
            id=p.id,
            title=p.title,
            authors=p.get_authors_list(),
        )
        for p in papers
    ]

    return {
        "total_items": total_items,
        "total_pages": (total_items + per_page - 1) // per_page,
        "page": page,
        "per_page": per_page,
        "items": parsed_papers,
    }


@app.get("/papers/{paper_id}/recommendations", response_model=List[schemas.PaperBase])
def get_recommendations(paper_id: str, db: Session = Depends(database.get_db)):
    print(f"\n--- Getting recommendations for paper_id: '{paper_id}' ---")

    try:
        retrieved_item = paper_collection.get(ids=[paper_id], include=["embeddings"])

        if not retrieved_item or not retrieved_item["ids"]:
            print(f"Error: Paper ID '{paper_id}' NOT FOUND in ChromaDB collection.")
            return []

        query_embedding = retrieved_item["embeddings"]

        results = paper_collection.query(
            query_embeddings=query_embedding, n_results=6  # Get top 5 + the item itself
        )

        recommended_ids = [pid for pid in results["ids"][0] if pid != paper_id]

        if not recommended_ids:
            print("No other similar papers found after excluding the source paper.")
            return []

        from sqlalchemy import case

        ordering = case(
            {id: i for i, id in enumerate(recommended_ids)}, value=models.Paper.id
        )
        papers = (
            db.query(models.Paper)
            .filter(models.Paper.id.in_(recommended_ids))
            .order_by(ordering)
            .all()
        )

        print(f"Successfully fetched {len(papers)} papers from SQLite.")

        return [
            schemas.PaperBase(
                id=p.id,
                title=p.title,
                authors=p.get_authors_list(),
            )
            for p in papers
        ]
    except Exception as e:
        # This can happen if the paper_id is not in ChromaDB
        print(f"Could not get recommendations for {paper_id}: {e}")
        return []


@app.get("/papers/{paper_id}", response_model=schemas.Paper)
def read_paper(paper_id: str, db: Session = Depends(database.get_db)):
    db_paper = db.query(models.Paper).filter(models.Paper.id == paper_id).first()
    if db_paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")

    return schemas.Paper(
        id=db_paper.id,
        title=db_paper.title,
        abstract=db_paper.abstract,
        authors=db_paper.get_authors_list(),
        contribution=db_paper.contribution,
        tasks=db_paper.get_tasks_list(),
        methods=db_paper.get_methods_list(),
        datasets=db_paper.get_datasets_list(),
        code_links=db_paper.get_code_links_list(),
    )


# --- Bookmark Endpoints ---


@app.post("/papers/{paper_id}/bookmark", status_code=status.HTTP_201_CREATED)
def create_bookmark(
    paper_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    db_paper = db.query(models.Paper).filter(models.Paper.id == paper_id).first()
    if not db_paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    existing_bookmark = (
        db.query(models.Bookmark)
        .filter(
            models.Bookmark.user_id == current_user.id,
            models.Bookmark.paper_id == paper_id,
        )
        .first()
    )
    if existing_bookmark:
        raise HTTPException(status_code=400, detail="Paper already bookmarked")

    new_bookmark = models.Bookmark(user_id=current_user.id, paper_id=paper_id)
    db.add(new_bookmark)
    db.commit()

    return {"detail": "Bookmark added successfully"}


@app.delete("/papers/{paper_id}/bookmark", status_code=status.HTTP_204_NO_CONTENT)
def delete_bookmark(
    paper_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    bookmark_to_delete = (
        db.query(models.Bookmark)
        .filter(
            models.Bookmark.user_id == current_user.id,
            models.Bookmark.paper_id == paper_id,
        )
        .first()
    )

    if not bookmark_to_delete:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    db.delete(bookmark_to_delete)
    db.commit()
    return


@app.get("/me/bookmarks", response_model=List[schemas.PaperBase])
def get_my_bookmarks(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    bookmarked_papers = (
        db.query(models.Paper)
        .join(models.Bookmark)
        .filter(models.Bookmark.user_id == current_user.id)
        .all()
    )
    return [
        schemas.PaperBase(id=p.id, title=p.title, authors=p.get_authors_list())
        for p in bookmarked_papers
    ]

from typing import List, Optional
from datetime import timedelta

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware

from . import auth, models, schemas, database

models.Base.metadata.create_all(bind=database.engine)

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
def login_for_access_token(db: Session = Depends(database.get_db), form_data: OAuth2PasswordRequestForm = Depends()):
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

    db_user = models.User(email=str(user.email), name=user.name, hashed_password=hashed_password)

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


@app.get("/users/me", response_model=schemas.User)
def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user


# --- Paper Endpoints ---
@app.get("/papers", response_model=schemas.PaginatedPaperResponse)
def read_papers(
    db: Session = Depends(database.get_db),
    page: int = 1,
    per_page: int = 12,
    search: Optional[str] = None,
    has_code: Optional[bool] = None,
):
    query = db.query(models.Paper)

    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            (models.Paper.title.ilike(search_term)) |
            (models.Paper.abstract.ilike(search_term))
        )

    if has_code is not None:
        if has_code:
            query = query.filter(models.Paper.code_links.isnot(None)).filter(models.Paper.code_links != '[]')
        else:
            query = query.filter((models.Paper.code_links.is_(None)) | (models.Paper.code_links == '[]'))

    total_items = query.count()

    offset = (page - 1) * per_page
    papers = query.offset(offset).limit(per_page).all()

    parsed_papers = [
        schemas.PaperBase(
            id=p.id,
            title=p.title,
            authors=p.get_authors_list(),
        ) for p in papers
    ]

    return {
        "total_items": total_items,
        "total_pages": (total_items + per_page - 1) // per_page,
        "page": page,
        "per_page": per_page,
        "items": parsed_papers,
    }


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
        current_user: models.User = Depends(auth.get_current_user)
):
    db_paper = db.query(models.Paper).filter(models.Paper.id == paper_id).first()
    if not db_paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    existing_bookmark = db.query(models.Bookmark).filter(
        models.Bookmark.user_id == current_user.id,
        models.Bookmark.paper_id == paper_id
    ).first()
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
        current_user: models.User = Depends(auth.get_current_user)
):
    bookmark_to_delete = db.query(models.Bookmark).filter(
        models.Bookmark.user_id == current_user.id,
        models.Bookmark.paper_id == paper_id
    ).first()

    if not bookmark_to_delete:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    db.delete(bookmark_to_delete)
    db.commit()
    return


@app.get("/me/bookmarks", response_model=List[schemas.PaperBase])
def get_my_bookmarks(
        db: Session = Depends(database.get_db),
        current_user: models.User = Depends(auth.get_current_user)
):
    bookmarked_papers = db.query(models.Paper).join(models.Bookmark).filter(
        models.Bookmark.user_id == current_user.id
    ).all()
    return [schemas.PaperBase(id=p.id, title=p.title, authors=p.get_authors_list())
            for p in bookmarked_papers]

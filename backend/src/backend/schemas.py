from pydantic import BaseModel, EmailStr
from typing import List, Optional

# --- Paper Schemas ---
class PaperBase(BaseModel):
    id: str
    title: str
    authors: List[str] = ()

class Paper(PaperBase):
    abstract: Optional[str] = None
    contribution: Optional[str] = None
    tasks: List[str] = ()
    methods: List[str] = ()
    datasets: List[str] = ()
    code_links: List[str] = ()

    class Config:
        from_attributes = True

class PaginatedPaperResponse(BaseModel):
    total_items: int
    total_pages: int
    page: int
    per_page: int
    items: List[PaperBase]

# --- User Schemas ---
class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int

    class Config:
        from_attributes = True

# --- Token Schemas (for Authentication) ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

import json
from sqlalchemy import Boolean, Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String)
    hashed_password = Column(String, nullable=False)

    bookmarks = relationship("Bookmark", back_populates="owner")

class Paper(Base):
    __tablename__ = "papers"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, index=True)
    abstract = Column(Text)
    authors = Column(Text)  # JSON string
    contribution = Column(Text)
    tasks = Column(Text) # JSON string
    methods = Column(Text) # JSON string
    datasets = Column(Text) # JSON string
    code_links = Column(Text) # JSON string
    processed = Column(Integer, default=0)

    def get_authors_list(self):
        if self.authors is None:
            return []

        authors = self.authors if self.authors.startswith('"') else f'"{self.authors}"'
        return json.loads(authors).split(",")

    def get_tasks_list(self):
        return json.loads(self.tasks if len(self.tasks.strip("'").strip('"')) > 0 else '[]')

    def get_methods_list(self):
        return json.loads(self.methods if len(self.methods.strip("'").strip('"')) > 0 else '[]')

    def get_datasets_list(self):
        return json.loads(self.datasets if len(self.datasets.strip("'").strip('"')) > 0 else '[]')

    def get_code_links_list(self):
        return json.loads(self.code_links if len(self.code_links.strip("'").strip('"')) > 0 else '[]')

class Bookmark(Base):
    __tablename__ = "bookmarks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    paper_id = Column(String, ForeignKey("papers.id"))

    owner = relationship("User", back_populates="bookmarks")
    paper = relationship("Paper")

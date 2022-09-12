from es_library.db import Base
from sqlalchemy import Column, Integer, String


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer(), primary_key=True)
    isbn = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)

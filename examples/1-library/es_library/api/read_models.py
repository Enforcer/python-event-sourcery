from es_library.db import Base
from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.dialects.postgresql import JSONB


class BookReadModel(Base):
    __tablename__ = "books_read_model"

    id = Column(Integer(), primary_key=True)
    isbn = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    available = Column(Boolean(), nullable=False)
    copies_total = Column(Integer(), nullable=False)
    copies_available = Column(JSONB(), nullable=False)

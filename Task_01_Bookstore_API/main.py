"""BookStore REST API"""

import asyncio
from datetime import date
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field

app = FastAPI(
    title="BookStore API",
    description="Async CRUD API for managing books, with validation and filtering.",
    version="1.0.0",
)

# schema
class BookBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, examples=["Python"])
    author: str = Field(..., min_length=1, max_length=100, examples=["Arijit Jana"])
    isbn: str = Field(..., pattern=r"^\d{10}(\d{3})?$", examples=["9780441013593"])
    genre: Optional[str] = Field(None, max_length=50, examples=["Sci-Fi"])
    price: float = Field(..., gt=0, examples=[999.65])
    published_year: int = Field(..., ge=1000, le=date.today().year, examples=[1985])
    in_stock: bool = True


class BookCreate(BookBase):
    """Body for POST and PUT (full replacement)."""


class BookPatch(BaseModel):
    """Body for PATCH - every field optional."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    author: Optional[str] = Field(None, min_length=1, max_length=100)
    isbn: Optional[str] = Field(None, pattern=r"^\d{10}(\d{3})?$")
    genre: Optional[str] = Field(None, max_length=50)
    price: Optional[float] = Field(None, gt=0)
    published_year: Optional[int] = Field(None, ge=1000, le=date.today().year)
    in_stock: Optional[bool] = None


class Book(BookBase):
    id: int


# storage

books: dict[int, Book] = {}
_next_id = 1
_lock = asyncio.Lock()


def _isbn_taken(isbn: str, exclude_id: Optional[int] = None) -> bool:
    return any(b.isbn == isbn and b.id != exclude_id for b in books.values())


def _get_or_404(book_id: int) -> Book:
    book = books.get(book_id)
    if book is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with id {book_id} not found",
        )
    return book


# endpoints

@app.post("/books", response_model=Book, status_code=status.HTTP_201_CREATED, tags=["Books"])
async def create_book(payload: BookCreate):
    global _next_id
    async with _lock:
        if _isbn_taken(payload.isbn):
            raise HTTPException(status.HTTP_409_CONFLICT, "A book with this ISBN already exists")
        book = Book(id=_next_id, **payload.model_dump())
        books[book.id] = book
        _next_id += 1
    return book


@app.get("/books", response_model=list[Book], tags=["Books"])
async def list_books(
    author: Optional[str] = Query(None, description="Case-insensitive author match"),
    genre: Optional[str] = Query(None, description="Case-insensitive genre match"),
    q: Optional[str] = Query(None, description="Search in title"),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    in_stock: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    results = list(books.values())
    if author:
        results = [b for b in results if author.lower() in b.author.lower()]
    if genre:
        results = [b for b in results if b.genre and genre.lower() == b.genre.lower()]
    if q:
        results = [b for b in results if q.lower() in b.title.lower()]
    if min_price is not None:
        results = [b for b in results if b.price >= min_price]
    if max_price is not None:
        results = [b for b in results if b.price <= max_price]
    if in_stock is not None:
        results = [b for b in results if b.in_stock == in_stock]
    return results[skip : skip + limit]


@app.get("/books/{book_id}", response_model=Book, tags=["Books"])
async def get_book(book_id: int):
    return _get_or_404(book_id)


@app.put("/books/{book_id}", response_model=Book, tags=["Books"])
async def replace_book(book_id: int, payload: BookCreate):
    async with _lock:
        _get_or_404(book_id)
        if _isbn_taken(payload.isbn, exclude_id=book_id):
            raise HTTPException(status.HTTP_409_CONFLICT, "A book with this ISBN already exists")
        book = Book(id=book_id, **payload.model_dump())
        books[book_id] = book
    return book


@app.patch("/books/{book_id}", response_model=Book, tags=["Books"])
async def update_book(book_id: int, payload: BookPatch):
    async with _lock:
        existing = _get_or_404(book_id)
        changes = payload.model_dump(exclude_unset=True)
        if "isbn" in changes and _isbn_taken(changes["isbn"], exclude_id=book_id):
            raise HTTPException(status.HTTP_409_CONFLICT, "A book with this ISBN already exists")
        book = existing.model_copy(update=changes)
        books[book_id] = book
    return book


@app.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Books"])
async def delete_book(book_id: int):
    async with _lock:
        _get_or_404(book_id)
        del books[book_id]

# BookStore REST API

An asynchronous CRUD API built with **FastAPI** and **Pydantic** to manage a book catalogue. It supports automatic book IDs, ISBN uniqueness checks, search, filtering, pagination, and interactive OpenAPI documentation.

Developed by **Avik Dey** for the **Datheon FastAPI Internship**.

## Features

- Create, list, retrieve, replace, partially update, and delete books.
- Validate request bodies using Pydantic schemas.
- Reject duplicate ISBNs when creating or updating a book.
- Filter by author, genre, title, price range, and stock availability.
- Paginate results using `skip` and `limit`.
- Explore and call endpoints through Swagger UI.
- Serialize write operations using an `asyncio.Lock` within one application process.

## Technology Stack

| Technology   | Purpose                                                              |
| ------------ | -------------------------------------------------------------------- |
| Python 3.10+ | Application language; supports the type annotations used in the code |
| FastAPI      | Routing, request handling, response schemas, and OpenAPI generation  |
| Pydantic 2   | Request validation and data models                                   |
| Uvicorn      | ASGI server that runs the application                                |
| asyncio      | Lock used to coordinate writes within one process                    |

## Project Structure

Save the supplied API code as `main.py`. For this single-file task, use the following layout:

```text
bookstore/
    main.py             # Schemas, storage, helper functions, and endpoints
    README.md           # Installation, architecture, and usage
```

The sections below assume your terminal is open inside `bookstore`, alongside `main.py`.

## Installation and Setup

### 1. Create a virtual environment

```bash
python3 -m venv .venv
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install "fastapi>=0.100.0,<1.0" "pydantic>=2.0,<3.0" "uvicorn[standard]"
```

To record the installed dependency versions for the repository:

```bash
python -m pip freeze > requirements.txt
```

Future installations can then use `python -m pip install -r requirements.txt`.

### 3. Start the server

```bash
python -m uvicorn main:app --reload
```

Here, `main` refers to `main.py`, and `app` refers to the `FastAPI` instance inside it. Run this command from the directory containing `main.py`. The `--reload` option restarts the server when development files change.

The server runs at [http://127.0.0.1:8000](http://127.0.0.1:8000). Stop it with **Control + C**, including on macOS.

## API Documentation

| Resource     | Local URL                                                                |
| ------------ | ------------------------------------------------------------------------ |
| Swagger UI   | [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)                 |
| ReDoc        | [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)               |
| OpenAPI JSON | [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json) |

These addresses work while the server is running on your computer. No endpoint is defined at `/`; use `/docs` to explore the API.

## Architecture

The application uses a single-file structure with four logical components:

| Component | Implementation                                | Responsibility                                                    |
| --------- | --------------------------------------------- | ----------------------------------------------------------------- |
| Schemas   | `BookBase`, `BookCreate`, `BookPatch`, `Book` | Define book fields, request validation, and response structure    |
| Routes    | Async endpoint functions                      | Receive HTTP requests, apply filters, and perform CRUD operations |
| Helpers   | `_get_or_404`, `_isbn_taken`                  | Find books and check ISBN uniqueness                              |
| Storage   | `books`, `_next_id`, `_lock`                  | Hold book records, assign IDs, and coordinate writes              |

FastAPI receives a request and validates its path, query parameters, and body. The endpoint then uses the helper functions and in-memory dictionary to read or change records. FastAPI serializes successful responses using the declared response model; errors return the corresponding HTTP status and error details.

`books` maps integer IDs to `Book` objects. `_next_id` begins at `1` and increases after each successful creation. Clients do not need to submit an ID. Deleted IDs are not reused during the same application process.

POST, PUT, PATCH, and DELETE acquire `_lock` before modifying storage. The lock is local to one process; it does not coordinate multiple server workers. All routes are declared with `async def`, while the current storage operations run directly in memory.

## Book Fields and Validation

| Field            | Type           | Rules and defaults                                                              |
| ---------------- | -------------- | ------------------------------------------------------------------------------- |
| `id`             | Integer        | Generated by the server; returned in book responses                             |
| `title`          | String         | Required for POST/PUT; 1–200 characters                                         |
| `author`         | String         | Required for POST/PUT; 1–100 characters                                         |
| `isbn`           | String         | Required for POST/PUT; matches the 10- or 13-digit pattern and must be unique   |
| `genre`          | String or null | Optional; maximum 50 characters; defaults to null                               |
| `price`          | Float          | Required for POST/PUT; greater than zero                                        |
| `published_year` | Integer        | Required for POST/PUT; between 1000 and the year captured when the module loads |
| `in_stock`       | Boolean        | Defaults to `true` for POST/PUT                                                 |

The ISBN rule checks the digit pattern only; it does not verify an ISBN checksum. String length checks do not trim whitespace, and the schemas use Pydantic's default type conversion rather than strict validation.

## Endpoints

| Method | Path               | Purpose                          | Success status   |
| ------ | ------------------ | -------------------------------- | ---------------- |
| POST   | `/books`           | Create a book                    | `201 Created`    |
| GET    | `/books`           | List, filter, and paginate books | `200 OK`         |
| GET    | `/books/{book_id}` | Retrieve one book                | `200 OK`         |
| PUT    | `/books/{book_id}` | Replace a book                   | `200 OK`         |
| PATCH  | `/books/{book_id}` | Update selected fields           | `200 OK`         |
| DELETE | `/books/{book_id}` | Delete a book                    | `204 No Content` |

PUT uses `BookCreate`: all required fields must be supplied, and omitted `genre` and `in_stock` values reset to their defaults. PATCH uses `BookPatch`: omitted fields retain their current values. DELETE returns an empty response body.

### Query Parameters for GET /books

| Parameter   | Behavior                                        | Default   |
| ----------- | ----------------------------------------------- | --------- |
| `author`    | Case-insensitive substring match                | No filter |
| `genre`     | Case-insensitive exact match                    | No filter |
| `q`         | Case-insensitive title substring search         | No filter |
| `min_price` | Inclusive lower price bound; must be at least 0 | No filter |
| `max_price` | Inclusive upper price bound; must be at least 0 | No filter |
| `in_stock`  | Match `true` or `false`                         | No filter |
| `skip`      | Number of matching records to skip; at least 0  | `0`       |
| `limit`     | Maximum records returned; between 1 and 100     | `10`      |

Filters are combined before pagination. The response is a JSON array without a total-count wrapper. A `min_price` greater than `max_price` currently returns an empty array.

## Usage Examples

### Create a book

```bash
curl -X POST "http://127.0.0.1:8000/books" \
  -H "Content-Type: application/json" \
  -d '{"title":"Python","author":"Arijit Jana","isbn":"9780441013593","genre":"Programming","price":999.65,"published_year":2025,"in_stock":true}'
```

Example response from a fresh server (`201 Created`):

```json
{
  "title": "Python",
  "author": "Arijit Jana",
  "isbn": "9780441013593",
  "genre": "Programming",
  "price": 999.65,
  "published_year": 2025,
  "in_stock": true,
  "id": 1
}
```

### Search and filter books

```bash
curl "http://127.0.0.1:8000/books?q=python&min_price=100&max_price=1000&in_stock=true&skip=0&limit=10"
```

### Retrieve a book

```bash
curl "http://127.0.0.1:8000/books/1"
```

### Replace a book

```bash
curl -X PUT "http://127.0.0.1:8000/books/1" \
  -H "Content-Type: application/json" \
  -d '{"title":"Advanced Python","author":"Arijit Jana","isbn":"9780441013593","genre":"Programming","price":899.0,"published_year":2025,"in_stock":true}'
```

### Update selected fields

```bash
curl -X PATCH "http://127.0.0.1:8000/books/1" \
  -H "Content-Type: application/json" \
  -d '{"price":799.0,"in_stock":false}'
```

### Delete a book

```bash
curl -i -X DELETE "http://127.0.0.1:8000/books/1"
```

## Error Handling

| Status                     | Trigger                                       |
| -------------------------- | --------------------------------------------- |
| `404 Not Found`            | The requested book ID does not exist          |
| `409 Conflict`             | An ISBN is already assigned to another book   |
| `422 Unprocessable Entity` | Request body, path, or query validation fails |

Example missing-book response:

```json
{
  "detail": "Book with id 99 not found"
}
```

## Manual Verification

Use Swagger UI's **Try it out** button to check the following workflow:

1. Create a book and confirm `201` with a generated ID.
2. List books and retrieve the new book by ID.
3. Create another book with the same ISBN and confirm `409`.
4. Submit a negative price or malformed ISBN and confirm `422`.
5. Replace the book with PUT and change selected fields with PATCH.
6. Try the search, stock, and pagination parameters.
7. Delete the book, confirm `204`, and retrieve it again to confirm `404`.

This is a suggested verification checklist; no automated test suite is included in the supplied code.

## Current Limitations

- Storage is in memory. Restarting the server, including an automatic reload, clears all books and resets the ID counter.
- Run with one worker. Separate workers have independent dictionaries, locks, and ID counters.
- PATCH currently accepts explicit `null` for every field and uses `model_copy(update=...)` without revalidation. Setting a required book field to `null` can store invalid data and cause a response-validation error. Omit unchanged fields; `genre` is the nullable field in the complete book model.
- Authentication, authorization, a persistent database, and deployment configuration are not implemented. This version is an internship demonstration; those features and stronger PATCH validation are needed before production use.


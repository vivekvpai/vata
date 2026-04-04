# Vata Run And API Testing Guide

This guide walks through the backend setup, starting the server, opening the FastAPI docs, and testing each API with the correct path parameters and JSON payloads.

## 1. Open the project root

Run all backend commands from the project root:

```bash
cd /mnt/c/Users/micro/Desktop/vata
```

On Windows PowerShell, use:

```powershell
cd C:\Users\micro\Desktop\vata
```

## 2. Activate your virtual environment

If you already created a virtual environment, activate it first.

WSL / Linux:

```bash
source venv/bin/activate
```

PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

## 3. Install backend dependencies

Install the project in editable mode:

```bash
pip install -e .
```

## 4. Start the FastAPI backend

Use this command from the repo root:

```bash
uvicorn vata.main:app --app-dir src --reload --port 8000
```

If you want to use the CLI entrypoint instead, use:

```bash
vata --reload
```

Note: in this environment, `vata` behaves like a single-command CLI, so `vata start --reload` may fail with `Got unexpected extra argument (start)`.

## 5. Open FastAPI docs for testing

Once the server is running, open:

- App root: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`
- OpenAPI schema: `http://127.0.0.1:8000/openapi.json`

Use `/docs` for manual testing:

1. Open `http://127.0.0.1:8000/docs`
2. Expand the endpoint you want
3. Click `Try it out`
4. Fill in the path parameter and request body
5. Click `Execute`

## 6. Important API behavior

For category endpoints, the path parameter is the category name, not the JSON filename.

Example:

- Category name: `starter`
- Generated file: `starter_20260403060316.json`

Use:

```text
/api/categories/starter
```

Do not use:

```text
/api/categories/starter_20260403060316
```

The backend uses `category.json` to map a category name like `starter` to its latest file internally.

## 7. Valid JSON rules

All request bodies must be valid JSON.

Invalid:

```json
{
  "category": "starter",
  "data": {
    "additionalProp1": {abcd}
  }
}
```

Valid string value:

```json
{
  "category": "starter",
  "data": {
    "additionalProp1": "abcd"
  }
}
```

Valid nested object:

```json
{
  "category": "starter",
  "data": {
    "additionalProp1": {
      "value": "abcd"
    }
  }
}
```

## 8. API reference

### GET `/api/hello`

Simple health check endpoint.

No body required.

Example response:

```json
{
  "message": "Hello from Vata backend!"
}
```

### POST `/api/categories`

Creates a new category file and registers it in `src/vata/data/category.json`.

Request body:

```json
{
  "category": "starter",
  "data": {
    "name": "test",
    "count": 1,
    "active": true
  }
}
```

Rules:

- `category` is required
- `category` must not be empty
- `data` must be a valid JSON object

Example response:

```json
{
  "message": "Category file created",
  "category": "starter",
  "filename": "starter_20260403060316.json"
}
```

### GET `/api/categories`

Lists all categories from the registry.

No body required.

Example response:

```json
{
  "starter": [
    "starter_20260403060316.json"
  ]
}
```

### GET `/api/categories/{category}`

Returns the latest file content for a category.

Path parameter:

- `category`: category name such as `starter`

Example path:

```text
/api/categories/starter
```

Example response:

```json
{
  "category": "starter",
  "filename": "starter_20260403060316.json",
  "files": [
    "starter_20260403060316.json"
  ],
  "content": {
    "category": "starter",
    "created_at": "2026-04-03T06:03:16.000000+00:00",
    "data": {
      "name": "test"
    }
  }
}
```

### PUT `/api/categories/{category}`

Updates the latest file for a category.

Path parameter:

- `category`: category name such as `starter`

Correct path:

```text
/api/categories/starter
```

Request body:

```json
{
  "data": {
    "additionalProp1": "just testing the PUT API"
  }
}
```

Example response:

```json
{
  "message": "Category file updated",
  "category": "starter",
  "filename": "starter_20260403060316.json",
  "content": {
    "category": "starter",
    "created_at": "2026-04-03T06:03:16.000000+00:00",
    "updated_at": "2026-04-03T06:10:00.000000+00:00",
    "data": {
      "additionalProp1": "just testing the PUT API"
    }
  }
}
```

### DELETE `/api/categories/{category}`

Deletes all files registered under a category and removes that category from the registry.

Path parameter:

- `category`: category name such as `starter`

Example path:

```text
/api/categories/starter
```

No request body required.

Example response:

```json
{
  "message": "Category deleted",
  "category": "starter"
}
```

## 9. Quick test flow

Use this order when manually testing from `/docs`:

1. Call `GET /api/hello`
2. Call `POST /api/categories` with category `starter`
3. Call `GET /api/categories`
4. Call `GET /api/categories/starter`
5. Call `PUT /api/categories/starter`
6. Call `GET /api/categories/starter` again to verify the update
7. Call `DELETE /api/categories/starter`

## 10. Common errors

### Error: `JSON decode error`

Cause:

- The request body is not valid JSON

Fix:

- Make sure all keys and string values use double quotes
- Do not send values like `{abcd}`

### Error: HTML page returned instead of JSON

Cause:

- The category path parameter does not exist
- The frontend SPA fallback is returning `index.html` for a 404

Fix:

- Use the category name, such as `starter`
- Do not use the generated filename in the path

### Error: `Got unexpected extra argument (start)`

Cause:

- The installed `vata` CLI is being treated as a single-command app

Fix:

- Use `vata --reload`
- Or run `uvicorn vata.main:app --app-dir src --reload --port 8000`


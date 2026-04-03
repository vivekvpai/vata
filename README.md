# Vata

Vata is a local-first Knowledge Graph application built with FastAPI and React.

## Project Structure

- `frontend/`: React + Vite source code (TypeScript + SWC).
- `src/vata/`: Python backend source code.
  - `main.py`: FastAPI server logic.
  - `cli.py`: Typer CLI entry point.
  - `frontend_dist/`: Location where the production frontend build is served from.

## Getting Started

### 1. Build the Frontend

Navigate to the `frontend` directory, install dependencies, and build the static assets:

```bash
cd frontend
npm install
npm run build
```

This will output the compiled React app into `src/vata/frontend_dist/`.

### 2. Install the Python Package

Return to the root directory and install `vata` in editable mode:

```bash
cd ..
pip install -e .
```

### 3. Run the Application

Start the Vata server and open the UI automatically:

```bash
vata start
```

The application will be available at [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Development

For a live development experience with hot-reloading on both frontend and backend:

### 1. Start the Backend (FastAPI)

From the **root directory** (not the `frontend` folder):

```bash
uvicorn vata.main:app --app-dir src --reload --port 8000
```

### 2. Start the Frontend (Vite)

In a **new terminal window**, navigate to the `frontend` directory:

```bash
cd frontend
npm run dev
```

The frontend will be available at [http://localhost:5173](http://localhost:5173). It is pre-configured to proxy API requests to the backend on port 8000.

## API Testing Guide

For a step-by-step backend run and API testing guide, see [README_API_TESTING.md](README_API_TESTING.md).

## Tech Stack

- **Backend**: Python 3.12, FastAPI, Uvicorn, Typer.
- **Frontend**: React 18, Vite, TypeScript.
- **Packaging**: Pyproject.toml (Hatchling).

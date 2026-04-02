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

## Tech Stack

- **Backend**: Python 3.12, FastAPI, Uvicorn, Typer.
- **Frontend**: React 18, Vite, TypeScript.
- **Packaging**: Pyproject.toml (Hatchling).

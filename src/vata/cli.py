import typer
import uvicorn
import webbrowser
import threading
import time

from vata.services.category_service import ensure_data_dir

# Create the Typer app with an explicit name to avoid auto-merging
app = typer.Typer(help="Vata CLI - Local-First Knowledge Graph")

# Define a main callback. This ensures 'vata' remains a command 
# container and subcommands like 'start' are explicitly required.
@app.callback()
def main():
    """Knowledge Graph management on your local machine."""
    pass

def open_browser(host: str, port: int):
    """Wait for server to start, then open the browser."""
    time.sleep(1.5)
    webbrowser.open(f"http://{host}:{port}")

@app.command()
def start(
    host: str = "127.0.0.1",
    port: int = 8000,
    reload: bool = False
):
    """Launch the Vata server and open the web UI."""
    typer.echo(f"Starting Vata at http://{host}:{port}")
    
    # Ensure data directory exists before starting
    ensure_data_dir()
    
    # Start browser in a background thread
    threading.Thread(target=open_browser, args=(host, port), daemon=True).start()
    
    # Launch Uvicorn
    # Note: Using "vata.main:app" string format allows --reload to work
    uvicorn.run("vata.main:app", host=host, port=port, reload=reload)

if __name__ == "__main__":
    app()

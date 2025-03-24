import argparse
from src.cli import ZerePyCLI

# Import action modules to register them
import src.actions.twitter_actions  
import src.actions.echochamber_actions
import src.actions.solana_actions
import src.actions.ollama_actions  # Import the new Ollama actions
import src.actions.api_tools_actions  # Import the API tools actions

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='ZerePy - AI Agent Framework')
    parser.add_argument('--server', action='store_true', help='Run in server mode')
    parser.add_argument('--host', default='0.0.0.0', help='Server host (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8000, help='Server port (default: 8000)')
    args = parser.parse_args()

    if args.server:
        try:
            from src.server import start_server
            start_server(host=args.host, port=args.port)
        except ImportError:
            print("Server dependencies not installed. Run: poetry install --extras server")
            exit(1)
    else:
        cli = ZerePyCLI()
        cli.main_loop()
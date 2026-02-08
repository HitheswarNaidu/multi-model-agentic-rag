import argparse
import shutil
import sys
from pathlib import Path

# Ensure src is in path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from rag.pipeline import UPLOAD_DIR, load_pipeline


def print_help():
    print("\nCommands:")
    print("  /upload <path>  : Copy a file to the upload directory and re-index")
    print("  /clear          : Clear conversation memory")
    print("  /exit           : Exit the CLI")
    print("  /help           : Show this help")

def main():
    parser = argparse.ArgumentParser(description="Multimodal RAG CLI")
    parser.add_argument("--query", type=str, help="Run a single query and exit")
    args = parser.parse_args()

    print("Loading RAG Pipeline...")
    pipeline = load_pipeline()

    # If single query mode
    if args.query:
        print(f"\nQ: {args.query}")
        result = pipeline.query(args.query)
        print(f"A: {result['llm'].get('answer')}")
        return

    # Interactive mode
    print("\n=== Multimodal RAG CLI ===")
    print("Type your question or a command (type /help for commands).")

    while True:
        try:
            user_input = input("\n> ").strip()
            if not user_input:
                continue

            if user_input.lower() == "/exit":
                break
            elif user_input.lower() == "/help":
                print_help()
                continue
            elif user_input.lower() == "/clear":
                pipeline.memory.clear()
                print("Memory cleared.")
                continue
            elif user_input.lower().startswith("/upload "):
                path_str = user_input[8:].strip()
                source_path = Path(path_str)
                if not source_path.exists():
                    print(f"File not found: {source_path}")
                    continue

                dest_path = UPLOAD_DIR / source_path.name
                shutil.copy(source_path, dest_path)
                print(f"Copied to {dest_path}. Indexing...")

                summary = pipeline.ingest_uploads()
                print(f"Indexed {summary.get('files_indexed')} files.")
                continue

            # Normal query
            print("Thinking...")
            result = pipeline.query(user_input)

            rewritten = result.get("rewritten_query")
            if rewritten and rewritten != user_input:
                print(f"(Interpreted: {rewritten})")

            answer = result['llm'].get('answer')
            print(f"\nAI: {answer}")

            prov = result['llm'].get('provenance', [])
            if prov:
                print(f"\n[Sources: {', '.join(prov)}]")

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\nError: {e}")

if __name__ == "__main__":
    main()

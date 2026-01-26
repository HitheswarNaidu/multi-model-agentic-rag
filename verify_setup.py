import sys
import shutil
from pathlib import Path
import importlib

REQUIRED_PACKAGES = [
    "streamlit",
    "docling",
    "chromadb",
    "whoosh",
    "sentence_transformers",
    "google.genai",
    "langchain",
    "pydantic",
    "pandas",
    "dotenv"
]

REQUIRED_DIRS = [
    "data/uploads",
    "data/indices/bm25",
    "data/indices/vector",
    "output/logs",
    "output/answers"
]

def check_python():
    print(f"✅ Python {sys.version.split()[0]}")
    if sys.version_info < (3, 10):
        print("❌ Warning: Python 3.10+ is recommended.")

def check_imports():
    print("\nChecking dependencies...")
    all_good = True
    for pkg in REQUIRED_PACKAGES:
        try:
            importlib.import_module(pkg)
            print(f"✅ {pkg}")
        except ImportError:
            print(f"❌ {pkg} NOT FOUND")
            all_good = False
    return all_good

def check_dirs():
    print("\nChecking directories...")
    root = Path(__file__).parent
    for d in REQUIRED_DIRS:
        path = root / d
        if path.exists():
            print(f"✅ {d} exists")
        else:
            print(f"⚠️ {d} missing (will be created by app)")

def check_env():
    print("\nChecking configuration...")
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        print("✅ .env found")
    else:
        print("❌ .env missing. Copy .env.example to .env")

def main():
    print("=== Multimodal RAG Environment Check ===\n")
    check_python()
    if not check_imports():
        print("\n❌ Missing dependencies. Run: pip install -r requirements.txt")
    else:
        check_dirs()
        check_env()
        print("\n✅ Setup looks good! Run 'streamlit run app/main.py' to start.")

if __name__ == "__main__":
    main()

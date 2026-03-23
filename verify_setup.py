from __future__ import annotations

import argparse
import importlib
import importlib.util
import sys
from pathlib import Path

REQUIRED_PACKAGES = [
    "llama_parse",
    "chromadb",
    "whoosh",
    "langchain",
    "langchain_nvidia_ai_endpoints",
    "langchain_groq",
    "langchain_openai",
    "pydantic",
    "pandas",
    "dotenv",
    "fastapi",
    "uvicorn",
]

REQUIRED_DIRS = [
    "data/uploads",
    "data/indices/versions",
    "output/logs",
    "output/answers",
]


def check_python() -> bool:
    print(f"Python {sys.version.split()[0]}")
    return True


def check_env(root: Path) -> bool:
    env_path = root / ".env"
    if env_path.exists():
        print("OK: .env found")
        return True
    print("ERROR: .env missing. Copy .env.example to .env")
    return False


def check_dirs(root: Path) -> bool:
    ok = True
    for rel in REQUIRED_DIRS:
        path = root / rel
        if path.exists():
            print(f"OK: {rel} exists")
        else:
            print(f"WARN: {rel} missing (app will create it)")
            ok = ok and True
    return ok


def check_packages_quick() -> bool:
    ok = True
    print("Quick dependency probe (find_spec)...")
    for pkg in REQUIRED_PACKAGES:
        if importlib.util.find_spec(pkg) is None:
            print(f"ERROR: {pkg} NOT FOUND")
            ok = False
        else:
            print(f"OK: {pkg}")
    return ok


def check_packages_full() -> bool:
    ok = True
    print("Full dependency import check...")
    for pkg in REQUIRED_PACKAGES:
        try:
            importlib.import_module(pkg)
            print(f"OK: {pkg}")
        except ImportError:
            print(f"ERROR: {pkg} NOT FOUND")
            ok = False
    return ok


def run(mode: str) -> int:
    root = Path(__file__).parent
    print(f"=== Multimodal RAG Environment Check ({mode}) ===")
    if not check_python():
        return 2
    if not check_env(root):
        return 2
    check_dirs(root)

    dep_ok = check_packages_full() if mode == "full" else check_packages_quick()
    if not dep_ok:
        print("ERROR: Missing dependencies. Install project requirements.")
        return 1

    print("OK: Setup check passed.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Environment verification for local launch.")
    parser.add_argument(
        "--mode",
        choices=["quick", "full"],
        default="quick",
        help="quick=lightweight checks, full=import-heavy checks",
    )
    args = parser.parse_args()
    return run(args.mode)


if __name__ == "__main__":
    raise SystemExit(main())

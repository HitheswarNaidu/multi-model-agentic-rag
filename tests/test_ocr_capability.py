import sys
from pathlib import Path

def test_rapidocr_import_and_init():
    try:
        from rapidocr_onnxruntime import RapidOCR
        engine = RapidOCR()
        print("✅ RapidOCR initialized successfully")
        return True
    except ImportError:
        print("❌ rapidocr_onnxruntime not found")
        return False
    except Exception as e:
        print(f"❌ RapidOCR init failed: {e}")
        return False

if __name__ == "__main__":
    test_rapidocr_import_and_init()

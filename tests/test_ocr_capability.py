import pytest


def test_rapidocr_import_and_init():
    rapidocr_module = pytest.importorskip("rapidocr_onnxruntime")
    engine = rapidocr_module.RapidOCR()
    assert engine is not None

if __name__ == "__main__":
    test_rapidocr_import_and_init()

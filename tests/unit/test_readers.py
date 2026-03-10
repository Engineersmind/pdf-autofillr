# """Unit tests for document readers."""
# import os
# import json
# import tempfile
# import pytest
# from uploaddocument.readers.reader_factory import ReaderFactory
# from uploaddocument.readers.json_reader import JsonReader
# from uploaddocument.readers.txt_reader import TxtReader


# def test_txt_reader():
#     with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
#         f.write("Hello investor, name is John Smith.")
#         path = f.name
#     try:
#         text = ReaderFactory.read(path)
#         assert "John Smith" in text
#     finally:
#         os.unlink(path)


# def test_json_reader():
#     with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
#         json.dump({"investor_name": "Jane Doe", "email": "jane@example.com"}, f)
#         path = f.name
#     try:
#         text = ReaderFactory.read(path)
#         assert "Jane Doe" in text
#         assert "email" in text
#     finally:
#         os.unlink(path)


# def test_unsupported_format():
#     with pytest.raises(ValueError, match="Unsupported"):
#         ReaderFactory.read("/nonexistent/file.xyz")


# def test_missing_file():
#     with pytest.raises(FileNotFoundError):
#         ReaderFactory.read("/no/such/file.txt")








"""Unit tests for document readers."""
import os
import json
import tempfile
import pytest
from uploaddocument.readers.reader_factory import ReaderFactory
from uploaddocument.readers.json_reader import JsonReader
from uploaddocument.readers.txt_reader import TxtReader


def test_txt_reader():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Hello investor, name is John Smith.")
        path = f.name
    try:
        text = ReaderFactory.read(path)
        assert "John Smith" in text
    finally:
        os.unlink(path)


def test_json_reader():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"investor_name": "Jane Doe", "email": "jane@example.com"}, f)
        path = f.name
    try:
        text = ReaderFactory.read(path)
        assert "Jane Doe" in text
        assert "email" in text
    finally:
        os.unlink(path)


def test_unsupported_format():
    # Must use a real file so ReaderFactory reaches the format check,
    # not the FileNotFoundError guard.
    with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
        path = f.name
    try:
        with pytest.raises(ValueError, match="Unsupported"):
            ReaderFactory.read(path)
    finally:
        os.unlink(path)


def test_missing_file():
    with pytest.raises(FileNotFoundError):
        ReaderFactory.read("/no/such/file.txt")
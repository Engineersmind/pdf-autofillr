"""
Tests for pdf_autofiller_mapper.exceptions

Verifies the exception hierarchy and APIError attributes.
No mocking required — pure class/attribute checks.
"""

import pytest
from pdf_autofiller_mapper.exceptions import (
    PDFMapperError,
    ConfigurationError,
    ExtractionError,
    MappingError,
    EmbeddingError,
    FillingError,
    APIError,
    ConnectionError,
    TimeoutError,
)


class TestExceptionHierarchy:
    """Every SDK exception must be catchable as PDFMapperError."""

    @pytest.mark.parametrize("exc_class", [
        ConfigurationError,
        ExtractionError,
        MappingError,
        EmbeddingError,
        FillingError,
        APIError,
        ConnectionError,
        TimeoutError,
    ])
    def test_is_subclass_of_pdf_mapper_error(self, exc_class):
        assert issubclass(exc_class, PDFMapperError)

    @pytest.mark.parametrize("exc_class", [
        ConfigurationError,
        ExtractionError,
        MappingError,
        EmbeddingError,
        FillingError,
        APIError,
        ConnectionError,
        TimeoutError,
    ])
    def test_is_catchable_as_base(self, exc_class):
        with pytest.raises(PDFMapperError):
            raise exc_class("test message")

    @pytest.mark.parametrize("exc_class", [
        ConfigurationError,
        ExtractionError,
        MappingError,
        EmbeddingError,
        FillingError,
        ConnectionError,
        TimeoutError,
    ])
    def test_is_also_exception(self, exc_class):
        assert issubclass(exc_class, Exception)


class TestAPIError:
    def test_message_only(self):
        err = APIError("something broke")
        assert str(err) == "something broke"
        assert err.status_code is None
        assert err.response_body is None

    def test_with_status_code(self):
        err = APIError("not found", status_code=404)
        assert "404" in str(err)
        assert err.status_code == 404

    def test_with_body(self):
        err = APIError("server error", status_code=500, response_body='{"error":"oops"}')
        assert err.response_body == '{"error":"oops"}'

    def test_catchable_as_pdf_mapper_error(self):
        with pytest.raises(PDFMapperError):
            raise APIError("bad", status_code=400)

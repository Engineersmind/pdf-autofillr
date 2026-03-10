"""Unit tests for APILogger."""
from uploaddocument.logging.api_logger import APILogger


def test_initial_state():
    logger = APILogger()
    s = logger.get_summary()
    assert s["summary"]["total_api_calls"] == 0
    assert s["summary"]["success"] is True


def test_log_request_and_response():
    logger = APILogger()
    logger.log_api_request("test_op", "https://api.example.com", {}, {"key": "value"})
    logger.log_api_response("test_op", 200, {"result": "ok"}, 0.5)
    s = logger.get_summary()
    assert s["summary"]["total_api_calls"] == 1


def test_log_error_marks_failure():
    logger = APILogger()
    logger.log_error("Something went wrong")
    s = logger.get_summary()
    assert s["summary"]["success"] is False
    assert s["summary"]["total_errors"] == 1


def test_log_process():
    logger = APILogger()
    logger.log_process("Step 1 complete")
    logger.log_process("Step 2 complete")
    s = logger.get_summary()
    assert s["summary"]["total_process_logs"] == 2

"""
test_all_entrypoints.py
-----------------------
Runs 2a → 2d in one go. Delete this file after testing.

Usage:
    python test_all_entrypoints.py          # all sections
    python test_all_entrypoints.py sdk      # 2a only
    python test_all_entrypoints.py cli      # 2b only
    python test_all_entrypoints.py fastapi  # 2c only
    python test_all_entrypoints.py lambda   # 2d only
"""

import os, sys, json, time, subprocess, threading, textwrap

# ── shared env so every section uses local/noop (no API keys needed) ──────────
os.environ.setdefault("RAGPDF_STORAGE",            "local")
os.environ.setdefault("RAGPDF_DATA_PATH",          "./ragpdf_data")
os.environ.setdefault("RAGPDF_VECTOR_STORE",       "local")
os.environ.setdefault("RAGPDF_EMBEDDING_BACKEND",  "noop")
os.environ.setdefault("RAGPDF_CORRECTOR_BACKEND",  "noop")
os.environ.setdefault("RAGPDF_API_KEY",            "test-key")
os.environ.setdefault("RAGPDF_PREDICTION_THRESHOLD", "0.0")   # noop embeddings → zero sim


# ── shared fixtures ────────────────────────────────────────────────────────────
FIELDS = [
    {"field_id": "f001", "field_name": "Investor Name",
     "context": "Full legal name of the investor",
     "section_context": "Investor Identity", "headers": ["Section 1", "Personal Info"]},
    {"field_id": "f002", "field_name": "Email",
     "context": "Email address for fund correspondence",
     "section_context": "Contact Details", "headers": ["Section 2", "Contact"]},
    {"field_id": "f003", "field_name": "Commitment Amount",
     "context": "Total capital commitment in USD",
     "section_context": "Investment Details", "headers": ["Section 4", "Subscription"]},
]

PDF_CATEGORY = {
    "category":      "Private Markets",
    "sub_category":  "Private Equity",
    "document_type": "LP Subscription Agreement",
}

LLM_PREDICTIONS = {"predictions": {
    "f001": {"predicted_field_name": "investor_full_name",   "confidence": 0.91},
    "f002": {"predicted_field_name": "investor_email",       "confidence": 0.88},
    "f003": {"predicted_field_name": "commitment_amount_usd","confidence": 0.95},
}}

FINAL_PREDICTIONS = {"final_predictions": {
    "f001": {"selected_field_name": "investor_full_name",    "selected_from": "llm", "llm_confidence": 0.91},
    "f002": {"selected_field_name": "investor_email",        "selected_from": "llm", "llm_confidence": 0.88},
    "f003": {"selected_field_name": "commitment_amount_usd", "selected_from": "llm", "llm_confidence": 0.95},
}}

ERRORS = [
    {"error_type": "wrong_field_name",
     "field_name": "investor_full_name",
     "feedback":   "Should be investor_full_legal_name",
     "field_type": "text",
     "page_number": 1}
]

USER, SESSION, PDF = "user_01", "session_01", "pdf_001"
PDF_HASH = "hash_abc123def456"


# ── helpers ────────────────────────────────────────────────────────────────────
def header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def ok(label, result):
    snippet = json.dumps(result)[:120].replace("\n", " ")
    print(f"  ✅  {label}: {snippet}...")

def fail(label, err):
    print(f"  ❌  {label}: {err}")
    raise SystemExit(1)


# ══════════════════════════════════════════════════════════════════════════════
# 2a — Python SDK
# ══════════════════════════════════════════════════════════════════════════════
def test_sdk():
    header("2a — Python SDK (RAGPDFClient direct)")

    from ragpdf import RAGPDFClient, LocalStorage, LocalVectorStore, NoOpCorrectorBackend
    from ragpdf.embeddings.noop_embeddings import NoOpEmbeddingBackend

    client = RAGPDFClient(
        storage          = LocalStorage("./ragpdf_data"),
        vector_store     = LocalVectorStore("./ragpdf_data"),
        embedding_backend= NoOpEmbeddingBackend(),
        corrector        = NoOpCorrectorBackend(),
    )

    # API 1
    try:
        r = client.get_predictions(USER, SESSION, PDF, FIELDS, PDF_HASH, PDF_CATEGORY)
        assert "submission_id" in r and "summary" in r
        ok("API 1 get_predictions", r)
    except Exception as e:
        fail("API 1", e)

    # API 2
    try:
        r = client.save_filled_pdf(USER, SESSION, PDF, LLM_PREDICTIONS, FINAL_PREDICTIONS)
        assert "metrics_summary" in r
        ok("API 2 save_filled_pdf", r)
    except Exception as e:
        fail("API 2", e)

    # API 4
    try:
        r = client.submit_feedback(USER, SESSION, PDF, ERRORS)
        assert "errors_processed" in r
        ok("API 4 submit_feedback", r)
    except Exception as e:
        fail("API 4", e)

    # API 5 — pdf
    try:
        r = client.get_metrics("pdf", user_id=USER, session_id=SESSION, pdf_id=PDF)
        assert r is not None
        ok("API 5 get_metrics(pdf)", r)
    except Exception as e:
        fail("API 5 pdf", e)

    # API 5 — global
    try:
        r = client.get_metrics("global")
        ok("API 5 get_metrics(global)", r)
    except Exception as e:
        fail("API 5 global", e)

    # API 6
    try:
        r = client.get_system_info()
        assert "summary" in r
        ok("API 6 get_system_info", r)
    except Exception as e:
        fail("API 6", e)

    # API 7
    try:
        r = client.get_error_analytics()
        assert r is not None
        ok("API 7 get_error_analytics", r)
    except Exception as e:
        fail("API 7", e)

    print("\n  ✅  2a PASSED — all SDK methods work\n")


# ══════════════════════════════════════════════════════════════════════════════
# 2b — CLI
# ══════════════════════════════════════════════════════════════════════════════
def test_cli():
    header("2b — CLI (ragpdf entrypoint)")

    import tempfile

    env = {**os.environ}

    def run(args):
        result = subprocess.run(
            ["ragpdf"] + args,
            capture_output=True, text=True, env=env
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr or result.stdout)
        return json.loads(result.stdout)

    # system-info
    try:
        r = run(["system-info"])
        assert "summary" in r
        ok("CLI system-info", r)
    except Exception as e:
        fail("CLI system-info", e)

    # predict — write fields to a temp file
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"fields": FIELDS, "pdf_hash": PDF_HASH, "pdf_category": PDF_CATEGORY}, f)
            fields_file = f.name

        r = run([
            "predict",
            "--user", USER, "--session", SESSION, "--pdf", "pdf_cli_test",
            "--fields",   fields_file,
            "--hash",     PDF_HASH,
            "--category", json.dumps(PDF_CATEGORY),
        ])
        assert "submission_id" in r
        ok("CLI predict", r)
    except Exception as e:
        fail("CLI predict", e)

    # metrics global
    try:
        r = run(["metrics", "--type", "global"])
        ok("CLI metrics --type global", r)
    except Exception as e:
        fail("CLI metrics", e)

    # feedback — write errors to a temp file
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"errors": ERRORS}, f)
            errors_file = f.name

        r = run(["feedback",
                 "--user", USER, "--session", SESSION, "--pdf", PDF,
                 "--errors", errors_file])
        assert "errors_processed" in r
        ok("CLI feedback", r)
    except Exception as e:
        fail("CLI feedback", e)

    # error-analytics
    try:
        r = run(["error-analytics"])
        ok("CLI error-analytics", r)
    except Exception as e:
        fail("CLI error-analytics", e)

    print("\n  ✅  2b PASSED — all CLI commands work\n")


# ══════════════════════════════════════════════════════════════════════════════
# 2c — FastAPI server
# ══════════════════════════════════════════════════════════════════════════════
def test_fastapi():
    header("2c — FastAPI server (ragpdf-server / uvicorn)")

    try:
        import httpx
    except ImportError:
        print("  ⚠️  httpx not installed — pip install httpx  — skipping 2c")
        return

    PORT = 8877
    BASE = f"http://127.0.0.1:{PORT}"
    HEADERS = {"x-api-key": "test-key", "Content-Type": "application/json"}

    # Start server in subprocess
    env = {**os.environ, "RAGPDF_SERVER_PORT": str(PORT)}
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn",
         "ragpdf.entrypoints.fastapi_app:app",
         "--host", "127.0.0.1", "--port", str(PORT)],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    # Wait for it to be ready
    ready = False
    for _ in range(20):
        time.sleep(0.5)
        try:
            httpx.get(f"{BASE}/health", timeout=1)
            ready = True
            break
        except Exception:
            pass

    if not ready:
        proc.terminate()
        fail("FastAPI server", "did not start within 10s")

    try:
        def post(path, body):
            r = httpx.post(f"{BASE}{path}", headers=HEADERS, json=body, timeout=10)
            r.raise_for_status()
            return r.json()

        def get(path):
            r = httpx.get(f"{BASE}{path}", headers=HEADERS, timeout=10)
            r.raise_for_status()
            return r.json()

        # health (no auth)
        r = httpx.get(f"{BASE}/health").json()
        ok("GET  /health", r)

        # API 1
        r = post("/predict", {
            "user_id": USER, "session_id": SESSION, "pdf_id": "pdf_api_test",
            "pdf_hash": PDF_HASH, "pdf_category": PDF_CATEGORY, "fields": FIELDS,
        })
        assert r["status"] == "success"
        ok("POST /predict", r)

        # API 2
        r = post("/save-filled-pdf", {
            "user_id": USER, "session_id": SESSION, "filled_doc_pdf_id": "pdf_api_test",
            "llm_predictions": LLM_PREDICTIONS, "final_predictions": FINAL_PREDICTIONS,
        })
        assert r["status"] == "success"
        ok("POST /save-filled-pdf", r)

        # API 4
        r = post("/feedback", {
            "user_id": USER, "session_id": SESSION, "pdf_id": "pdf_api_test",
            "errors": ERRORS,
        })
        assert r["status"] == "success"
        ok("POST /feedback", r)

        # API 5 — pdf
        r = post("/metrics", {
            "metric_type": "pdf",
            "user_id": USER, "session_id": SESSION, "pdf_id": "pdf_api_test",
        })
        assert r["status"] == "success"
        ok("POST /metrics (pdf)", r)

        # API 5 — global
        r = post("/metrics", {"metric_type": "global"})
        assert r["status"] == "success"
        ok("POST /metrics (global)", r)

        # API 6
        r = get("/system-info")
        assert r["status"] == "success"
        ok("GET  /system-info", r)

        # API 7
        r = post("/error-analytics", {})
        assert r["status"] == "success"
        ok("POST /error-analytics", r)

    finally:
        proc.terminate()
        proc.wait()

    print("\n  ✅  2c PASSED — all FastAPI endpoints work\n")


# ══════════════════════════════════════════════════════════════════════════════
# 2d — AWS Lambda entrypoint (local simulation)
# ══════════════════════════════════════════════════════════════════════════════
def test_lambda():
    header("2d — AWS Lambda entrypoint (local simulation)")

    from ragpdf.entrypoints.aws_lambda import lambda_handler

    def call(api_name, **payload):
        event = {
            "headers": {"x-api-key": "test-key"},
            "body": json.dumps({"api_name": api_name, **payload}),
        }
        resp = lambda_handler(event, None)
        body = json.loads(resp["body"])
        if resp["statusCode"] != 200:
            raise RuntimeError(f"HTTP {resp['statusCode']}: {body}")
        return body

    # API 1
    try:
        r = call("get_rag_predictions",
                 user_id=USER, session_id=SESSION, pdf_id="pdf_lambda_test",
                 pdf_hash=PDF_HASH, pdf_category=PDF_CATEGORY, fields=FIELDS)
        assert r["status"] == "success"
        ok("Lambda get_rag_predictions", r)
    except Exception as e:
        fail("Lambda API 1", e)

    # API 2
    try:
        r = call("saving_filled_pdf",
                 user_id=USER, session_id=SESSION, filled_doc_pdf_id="pdf_lambda_test",
                 llm_predictions=LLM_PREDICTIONS, final_predictions=FINAL_PREDICTIONS)
        assert r["status"] == "success"
        ok("Lambda saving_filled_pdf", r)
    except Exception as e:
        fail("Lambda API 2", e)

    # API 4
    try:
        r = call("user_feedback",
                 user_id=USER, session_id=SESSION, pdf_id="pdf_lambda_test",
                 errors=ERRORS)
        assert r["status"] == "success"
        ok("Lambda user_feedback", r)
    except Exception as e:
        fail("Lambda API 4", e)

    # API 5 — pdf
    try:
        r = call("get_metrics", metric_type="pdf",
                 user_id=USER, session_id=SESSION, pdf_id="pdf_lambda_test")
        assert r["status"] == "success"
        ok("Lambda get_metrics (pdf)", r)
    except Exception as e:
        fail("Lambda API 5 pdf", e)

    # API 5 — global
    try:
        r = call("get_metrics", metric_type="global")
        assert r["status"] == "success"
        ok("Lambda get_metrics (global)", r)
    except Exception as e:
        fail("Lambda API 5 global", e)

    # API 6
    try:
        r = call("get_system_info")
        assert r["status"] == "success"
        ok("Lambda get_system_info", r)
    except Exception as e:
        fail("Lambda API 6", e)

    # API 7
    try:
        r = call("get_error_analytics")
        assert r["status"] == "success"
        ok("Lambda get_error_analytics", r)
    except Exception as e:
        fail("Lambda API 7", e)

    # Bad API key
    try:
        event = {"headers": {"x-api-key": "wrong"}, "body": json.dumps({"api_name": "get_system_info"})}
        resp = lambda_handler(event, None)
        assert resp["statusCode"] == 401
        ok("Lambda 401 on bad key", {"statusCode": 401})
    except Exception as e:
        fail("Lambda auth check", e)

    # Unknown api_name
    try:
        event = {"headers": {"x-api-key": "test-key"}, "body": json.dumps({"api_name": "nonexistent"})}
        resp = lambda_handler(event, None)
        assert resp["statusCode"] == 400
        ok("Lambda 400 on unknown api_name", {"statusCode": 400})
    except Exception as e:
        fail("Lambda unknown route check", e)

    print("\n  ✅  2d PASSED — all Lambda routes work\n")


# ══════════════════════════════════════════════════════════════════════════════
# main
# ══════════════════════════════════════════════════════════════════════════════
SECTIONS = {"sdk": test_sdk, "cli": test_cli, "fastapi": test_fastapi, "lambda": test_lambda}

if __name__ == "__main__":
    target = sys.argv[1].lower() if len(sys.argv) > 1 else "all"

    if target == "all":
        for fn in SECTIONS.values():
            fn()
        print("\n" + "="*60)
        print("  🎉  ALL ENTRYPOINTS PASSED (2a → 2d)")
        print("="*60 + "\n")
    elif target in SECTIONS:
        SECTIONS[target]()
    else:
        print(f"Unknown section '{target}'. Choose: all | sdk | cli | fastapi | lambda")
        sys.exit(1)
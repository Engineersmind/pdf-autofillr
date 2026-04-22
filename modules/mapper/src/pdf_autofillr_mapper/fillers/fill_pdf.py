import os
import subprocess
import logging

from pdf_autofillr_mapper.utils.jar_path import find_jar

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def fill_with_java(
    embedded_pdf: str,
    input_json: str,
    output_path: str = None,
    storage_config: dict = None,
):
    """
    Fills PDF form using Java Itext utility.

    Args:
        embedded_pdf:   Path to the embedded PDF file (output from embed stage).
        input_json:     Path to the input JSON file with form data.
        output_path:    Explicit output path for the filled PDF. If not provided,
                        defaults to <embedded_pdf_base>_filled.pdf.
        storage_config: Storage configuration for output (currently unused).

    Returns:
        str: Path to the filled PDF.

    Raises:
        FileNotFoundError: If any required input file is missing.
        RuntimeError:      If the Java filling process fails or times out.
    """
    logger.info("[🧩] Starting PDF form filling with Java Itext utility...")

    # Use explicit output path if provided, otherwise derive from embedded PDF
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        filled_pdf = output_path
    elif "/tmp/" in embedded_pdf:
        base_name = os.path.splitext(os.path.basename(embedded_pdf))[0]
        filled_pdf = f"/tmp/{base_name}_filled.pdf"
    else:
        base_name = os.path.splitext(embedded_pdf)[0]
        filled_pdf = f"{base_name}_filled.pdf"

    jar_path = find_jar("filler.jar")
    logger.info(f"[📦] Found Java filler at: {jar_path}")

    # Validate required inputs
    for label, path in {"embedded_pdf": embedded_pdf, "input_json": input_json}.items():
        if not os.path.exists(path):
            logger.error(f"[❌] Missing required file for Java filling: {path}")
            raise FileNotFoundError(f"Missing required file ({label}): {path}")

    cmd = ["java", "-jar", jar_path, embedded_pdf, input_json, filled_pdf]
    logger.info(f"[🔧] Running Java command: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=300,
        )
        if result.stdout:
            logger.info(f"[📝] Java output: {result.stdout.strip()}")

        if not os.path.exists(filled_pdf):
            raise RuntimeError(f"Java process completed but output file not found: {filled_pdf}")

        logger.info(f"[✅] Java filling completed successfully. Output: {filled_pdf}")
        return filled_pdf

    except subprocess.TimeoutExpired as e:
        logger.error("[❌] Java filling process timed out after 5 minutes")
        raise RuntimeError("Java filling process timed out") from e

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() if e.stderr else "Unknown Java error"
        logger.error(f"[❌] Java filling failed: {error_msg}")
        if e.stdout:
            logger.error(f"[📝] Java stdout: {e.stdout.strip()}")
        raise RuntimeError(f"Java filling step failed: {error_msg}") from e

    except Exception as e:
        logger.error(f"[❌] Unexpected error during Java filling: {str(e)}")
        raise RuntimeError(f"Unexpected error in Java filling: {str(e)}") from e


async def fill_with_java_safe(
    embedded_pdf: str,
    input_json: str,
    storage_config: dict = None,
):
    """
    Non-raising wrapper around fill_with_java.

    Always returns a dict — never raises.

    Returns:
        {"status": "success", "pdf_file_path": <path>}
        {"status": "error",   "error": <message>, "pdf_file_path": None}
    """
    if not os.path.exists(embedded_pdf):
        logger.error(f"[❌] Embedded PDF file not found: {embedded_pdf}")
        return {
            "status": "error",
            "error": f"Embedded PDF file not found: {embedded_pdf}",
            "pdf_file_path": None,
        }
    try:
        filled_pdf = await fill_with_java(embedded_pdf, input_json, storage_config)
        return {"status": "success", "pdf_file_path": filled_pdf}
    except Exception as e:
        logger.error(f"[❌] Fill operation failed: {str(e)}")
        return {"status": "error", "error": str(e), "pdf_file_path": None}

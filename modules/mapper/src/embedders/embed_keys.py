import os
import subprocess
import logging

from src.utils.jar_path import find_jar

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_embed_java_stage(
    original_pdf: str,
    extracted_json: str, 
    mapping_json: str,
    radio_json: str,
    storage_config: dict = None
):
    """
    Rebuilds PDF form using Java utility with embedded form data.
    
    Args:
        original_pdf (str): Path to the original PDF file
        extracted_json (str): Path to the extracted JSON file
        mapping_json (str): Path to the mapped JSON file  
        radio_json (str): Path to the radio groups JSON file
        storage_config (dict): Storage configuration for output
        
    Returns:
        str: Path to the rebuilt PDF with embedded data
        
    Raises:
        FileNotFoundError: If any required input file is missing
        RuntimeError: If Java embedding process fails
    """
    logger.info("[🧩] Starting PDF form rebuilding with Java utility...")

    # Generate output path by adding _embedded suffix to original PDF
    if "/tmp/" in original_pdf:
        # For temp files, create output in /tmp/
        base_name = os.path.splitext(os.path.basename(original_pdf))[0]
        rebuilt_pdf = f"/tmp/{base_name}_embedded.pdf"
    else:
        # For local files, create output in same directory
        base_name = os.path.splitext(original_pdf)[0]
        rebuilt_pdf = f"{base_name}_embedded.pdf"
    
    jar_path = find_jar("rebuilder.jar")
    logger.info(f"[📦] Found Java rebuilder at: {jar_path}")
    
    # Validate all required input files exist
    required_files = {
        "original_pdf": original_pdf,
        "extracted_json": extracted_json, 
        "mapping_json": mapping_json,
        "radio_json": radio_json
    }
    
    for file_type, file_path in required_files.items():
        if not os.path.exists(file_path):
            logger.error(f"[❌] Missing required file for Java embedding: {file_path}")
            raise FileNotFoundError(f"Missing required file ({file_type}): {file_path}")
    
    # JAR validation is already done above in the search loop

    # Build command for Java subprocess
    cmd = [
        "java", "-jar", jar_path,
        original_pdf,
        extracted_json,
        mapping_json,
        radio_json,
        rebuilt_pdf
    ]
    
    logger.info(f"[🔧] Running Java command: {' '.join(cmd)}")

    try:
        # Execute Java subprocess
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=True,
            timeout=300  # 5 minute timeout
        )
        
        # Log successful execution
        # if result.stdout:
        #     logger.info(f"[📝] Java output: {result.stdout.strip()}")
            
        # Verify output file was created
        if not os.path.exists(rebuilt_pdf):
            raise RuntimeError(f"Java process completed but output file not found: {rebuilt_pdf}")
            
        logger.info(f"[✅] Java embedding completed successfully. Output: {rebuilt_pdf}")
        return rebuilt_pdf
        
    except subprocess.TimeoutExpired as e:
        logger.error("[❌] Java embedding process timed out after 5 minutes")
        raise RuntimeError("Java embedding process timed out") from e
        
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() if e.stderr else "Unknown Java error"
        logger.error(f"[❌] Java embedding failed: {error_msg}")
        
        # Log stdout for additional context
        if e.stdout:
            logger.error(f"[📝] Java stdout: {e.stdout.strip()}")
            
        raise RuntimeError(f"Java embedding step failed: {error_msg}") from e
        
    except Exception as e:
        logger.error(f"[❌] Unexpected error during Java embedding: {str(e)}")
        raise RuntimeError(f"Unexpected error in Java embedding: {str(e)}") from e
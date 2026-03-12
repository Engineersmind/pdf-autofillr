"""
pdf-autofillr-chatbot SDK
"""
from chatbot.client import chatbotClient
from chatbot.storage.local_storage import LocalStorage
from chatbot.storage.s3_storage import S3Storage
from chatbot.config.form_config import FormConfig
from chatbot.pdf.interface import PDFFillerInterface
from chatbot.pdf.mapper_filler import MapperPDFFiller
from chatbot.pdf.fill_report import FillReport
from chatbot.limits.rate_limiter import RateLimiter, RateLimitConfig, RateLimitExceeded

__version__ = "0.1.0"


def copy_sample_configs(destination: str = ".") -> None:
    """
    Copy bundled sample configs to destination/configs/.

    Run once after pip install:
        python -c "import chatbot; chatbot.copy_sample_configs('.')"
    """
    import shutil
    from pathlib import Path

    # Bundled inside the wheel at chatbot/config_samples/
    src = Path(__file__).parent / "config_samples"
    # Fallback for running from source repo
    if not src.exists():
        src = Path(__file__).parent.parent.parent / "config_samples"

    if not src.exists():
        raise FileNotFoundError(
            f"config_samples not found at {src}. Reinstall the package."
        )

    dst = Path(destination) / "configs"
    shutil.copytree(str(src), str(dst), dirs_exist_ok=True)
    print(f"✅ Configs copied to: {dst.resolve()}")
    print("   Edit files in configs/ to customise your form fields.")


__all__ = [
    "chatbotClient", "LocalStorage", "S3Storage", "FormConfig",
    "PDFFillerInterface", "MapperPDFFiller", "FillReport",
    "RateLimiter", "RateLimitConfig", "RateLimitExceeded",
    "copy_sample_configs",
]
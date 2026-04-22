"""
pdf-autofillr-mapper
====================
PDF field extraction, semantic mapping, embedding and filling engine.

Quick start::

    from pdf_autofillr_mapper import PDFPipeline

    import asyncio
    pipeline = PDFPipeline()
    result = asyncio.run(pipeline.run_all(
        input_pdf_path="./blank_form.pdf",
        input_data_path="./form_keys.json",
    ))
    print(result["final_output"])  # path to filled PDF
"""
from __future__ import annotations

__version__ = "1.0.0"
__all__ = ["PDFPipeline"]


def __getattr__(name: str):
    if name == "PDFPipeline":
        from pdf_autofillr_mapper.orchestrator import PDFPipeline
        return PDFPipeline
    import importlib
    try:
        return importlib.import_module(f"pdf_autofillr_mapper.{name}")
    except ImportError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def copy_sample_configs(destination: str = ".") -> None:
    """
    Copy bundled mapper sample configs to destination/configs/.

    Run once after pip install::

        python -c "import pdf_autofillr_mapper; pdf_autofillr_mapper.copy_sample_configs('.')"

    Copies:
        configs/mapper_config.ini     — LLM model, chunking, storage paths
        configs/.env.mapper.example   — API key template

    When using alongside pdf-autofillr-chatbot, the chatbot's
    copy_sample_configs() calls this automatically.
    """
    import shutil
    from pathlib import Path

    src = Path(__file__).parent / "config_samples"
    if not src.exists():
        raise FileNotFoundError(
            f"config_samples not found at {src}. "
            "Reinstall with: pip install --force-reinstall pdf-autofillr-mapper"
        )

    dst = Path(destination) / "configs"
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copytree(str(src), str(dst), dirs_exist_ok=True)
    print(f"Mapper configs copied to: {dst.resolve()}")
    print("  Edit configs/mapper_config.ini to configure LLM model, storage paths, etc.")

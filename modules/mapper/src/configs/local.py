"""
Local filesystem storage configuration.
"""

import os
import shutil
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from .base import BaseStorageConfig

logger = logging.getLogger(__name__)


class LocalStorageConfig(BaseStorageConfig):
    """Local filesystem storage implementation."""
    
    def __init__(self, base_dir: str = None):
        """
        Initialize local storage config.
        
        Args:
            base_dir: Optional base directory for output files (default: /tmp/pdf_processing)
        """
        super().__init__(source_type="local")
        self.base_dir = base_dir or "/tmp/pdf_processing"
        
        # Create base directory if it doesn't exist
        Path(self.base_dir).mkdir(parents=True, exist_ok=True)
    
    def parse_path(self, file_path: str) -> Dict[str, str]:
        """
        Parse local file path.
        
        Returns:
            {
                "type": "local",
                "path": "/full/path/to/file.ext",
                "directory": "/full/path/to",
                "filename": "file.ext"
            }
        """
        abs_path = os.path.abspath(file_path)
        directory = os.path.dirname(abs_path)
        filename = os.path.basename(abs_path)
        
        return {
            "type": "local",
            "path": abs_path,
            "directory": directory,
            "filename": filename
        }
    
    def download_file(self, source_path: str, local_path: str) -> str:
        """
        'Download' file (copy from source to destination for local).
        
        For local files, this is essentially a copy operation.
        """
        source_abs = os.path.abspath(source_path)
        dest_abs = os.path.abspath(local_path)
        
        # Create destination directory if needed
        os.makedirs(os.path.dirname(dest_abs), exist_ok=True)
        
        # Copy file
        shutil.copy2(source_abs, dest_abs)
        logger.info(f"Copied {source_abs} to {dest_abs}")
        return dest_abs
    
    def upload_file(self, local_path: str, destination_path: str) -> str:
        """
        'Upload' file (copy from source to destination for local).
        """
        source_abs = os.path.abspath(local_path)
        dest_abs = os.path.abspath(destination_path)
        
        # Create destination directory if needed
        os.makedirs(os.path.dirname(dest_abs), exist_ok=True)
        
        # Copy file
        shutil.copy2(source_abs, dest_abs)
        logger.info(f"Copied {source_abs} to {dest_abs}")
        return dest_abs
    
    def file_exists(self, file_path: str) -> bool:
        """Check if local file exists."""
        return os.path.exists(file_path)
    
    def generate_output_path(self, input_path: str, suffix: str, extension: str = None) -> str:
        """
        Generate local output path.
        
        Example:
            input: /path/to/file.pdf
            suffix: _extracted
            extension: .json
            output: /path/to/file_extracted.json
        """
        parsed = self.parse_path(input_path)
        
        # Get base path without extension
        path = parsed["path"]
        if '.' in path:
            base_path = path.rsplit('.', 1)[0]
            original_ext = '.' + path.rsplit('.', 1)[1]
        else:
            base_path = path
            original_ext = ''
        
        # Use provided extension or keep original
        new_ext = extension if extension else original_ext
        
        # Build new path
        return f"{base_path}{suffix}{new_ext}"
    
    def get_storage_config(self, file_path: str) -> Dict[str, Any]:
        """
        Get storage config for processing modules.
        
        Returns:
            {
                "type": "local",
                "path": "/full/path/to/file",
                "directory": "/full/path/to",
                "filename": "file.ext"
            }
        """
        return self.parse_path(file_path)
    
    def get_complete_file_config(
        self, 
        input_path: str, 
        user_id: Optional[int] = None,
        session_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate complete file configuration for local processing.
        
        Returns config with all pipeline paths in the same directory as input.
        """
        parsed = self.parse_path(input_path)
        
        # Generate session suffix if applicable
        session_suffix = ""
        if user_id is not None and session_id is not None:
            session_suffix = f"_user{user_id}_session{session_id}"
        
        # Base paths
        directory = parsed["directory"]
        filename = parsed["filename"]
        base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
        
        # Generate all pipeline paths in same directory
        config = {
            "source_type": "local",
            "input_path": parsed["path"],
            "input_filename": filename,
            "session_suffix": session_suffix,
            
            # Extraction stage outputs
            "extraction": {
                "extracted_path": os.path.join(directory, f"{base_name}{session_suffix}_extracted.json"),
                "radio_groups_path": os.path.join(directory, f"{base_name}{session_suffix}_radio_groups.json")
            },
            
            # Mapping stage outputs
            "mapping": {
                "mapping_path": os.path.join(directory, f"{base_name}{session_suffix}_mapped_fields.json"),
                "radio_groups_path": os.path.join(directory, f"{base_name}{session_suffix}_radio_groups.json")
            },
            
            # Embedding stage output
            "embedding": {
                "embedded_pdf_path": os.path.join(directory, f"{base_name}{session_suffix}_embedded.pdf")
            },
            
            # Filling stage output
            "filling": {
                "filled_pdf_path": os.path.join(directory, f"{base_name}{session_suffix}_filled.pdf")
            }
        }
        
        return config

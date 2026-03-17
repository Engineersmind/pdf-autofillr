"""
Mapper Resource

Methods for PDF field extraction, mapping, embedding, and filling.
"""

from typing import Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..client import PDFMapperClient


class MapperResource:
    """
    Resource for mapper operations.
    
    Provides methods for:
    - Extract: Extract fields from PDF
    - Map: Map fields to target schema
    - Embed: Embed metadata into PDF
    - Fill: Fill PDF with data
    - Make Embed File: Extract + Map + Embed pipeline
    - Check Embed File: Verify embedded metadata
    - Run All: Complete pipeline
    """
    
    def __init__(self, client: "PDFMapperClient"):
        """
        Initialize mapper resource.
        
        Args:
            client: PDF Mapper client instance
        """
        self.client = client
    
    def extract(
        self,
        pdf_path: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract fields from PDF.
        
        Args:
            pdf_path: Path to PDF file (S3 key, Azure blob, or local path)
            session_id: Optional session ID for tracking
            
        Returns:
            Extraction result with fields
            
        Example:
            ```python
            result = client.mapper.extract(
                pdf_path="s3://bucket/form.pdf"
            )
            print(result["data"]["fields"])
            ```
        """
        payload = {
            "pdf_path": pdf_path,
            "session_id": session_id,
        }
        return self.client._request("POST", "/extract", json=payload)
    
    def map(
        self,
        pdf_path: str,
        mapper_type: str = "ensemble",
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Map PDF fields to target schema.
        
        Args:
            pdf_path: Path to PDF file
            mapper_type: Mapper to use (semantic, rag, headers, ensemble)
            session_id: Optional session ID for tracking
            
        Returns:
            Mapping result
            
        Example:
            ```python
            result = client.mapper.map(
                pdf_path="s3://bucket/form.pdf",
                mapper_type="ensemble"
            )
            ```
        """
        payload = {
            "pdf_path": pdf_path,
            "mapper_type": mapper_type,
            "session_id": session_id,
        }
        return self.client._request("POST", "/map", json=payload)
    
    def embed(
        self,
        pdf_path: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Embed metadata into PDF.
        
        Args:
            pdf_path: Path to PDF file
            session_id: Optional session ID for tracking
            
        Returns:
            Embed result
            
        Example:
            ```python
            result = client.mapper.embed(
                pdf_path="s3://bucket/form.pdf"
            )
            ```
        """
        payload = {
            "pdf_path": pdf_path,
            "session_id": session_id,
        }
        return self.client._request("POST", "/embed", json=payload)
    
    def fill(
        self,
        pdf_path: str,
        data: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fill PDF form with data.
        
        Args:
            pdf_path: Path to PDF file
            data: Data to fill into the form
            session_id: Optional session ID for tracking
            
        Returns:
            Fill result
            
        Example:
            ```python
            result = client.mapper.fill(
                pdf_path="s3://bucket/form.pdf",
                data={
                    "first_name": "John",
                    "last_name": "Doe",
                    "email": "john@example.com"
                }
            )
            ```
        """
        payload = {
            "pdf_path": pdf_path,
            "data": data,
            "session_id": session_id,
        }
        return self.client._request("POST", "/fill", json=payload)
    
    def make_embed_file(
        self,
        pdf_path: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract + Map + Embed in one operation.
        
        Complete pipeline that extracts fields, maps them, and embeds
        the metadata into the PDF.
        
        Args:
            pdf_path: Path to PDF file
            session_id: Optional session ID for tracking
            
        Returns:
            Result of the complete operation
            
        Example:
            ```python
            result = client.mapper.make_embed_file(
                pdf_path="s3://bucket/form.pdf"
            )
            ```
        """
        payload = {
            "pdf_path": pdf_path,
            "session_id": session_id,
        }
        return self.client._request("POST", "/make-embed-file", json=payload)
    
    def check_embed_file(
        self,
        pdf_path: str
    ) -> Dict[str, Any]:
        """
        Check if PDF has embedded metadata.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Status indicating if metadata is embedded
            
        Example:
            ```python
            result = client.mapper.check_embed_file(
                pdf_path="s3://bucket/form.pdf"
            )
            if result["data"]["has_metadata"]:
                print("PDF has embedded metadata")
            ```
        """
        payload = {
            "pdf_path": pdf_path,
        }
        return self.client._request("POST", "/check-embed-file", json=payload)
    
    def run_all(
        self,
        pdf_path: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run complete pipeline (Extract + Map + Embed + Fill).
        
        Args:
            pdf_path: Path to PDF file
            session_id: Optional session ID for tracking
            
        Returns:
            Result of the complete pipeline
            
        Example:
            ```python
            result = client.mapper.run_all(
                pdf_path="s3://bucket/form.pdf"
            )
            ```
        """
        payload = {
            "pdf_path": pdf_path,
            "session_id": session_id,
        }
        return self.client._request("POST", "/run-all", json=payload)

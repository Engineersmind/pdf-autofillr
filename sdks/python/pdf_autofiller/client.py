"""
PDF Mapper API Client

Main client for interacting with the PDF Mapper API.
"""

import httpx
from typing import Optional, Dict, Any
from .resources.mapper import MapperResource


class PDFMapperClient:
    """
    Client for PDF Mapper API.
    
    Example:
        ```python
        client = PDFMapperClient(
            api_key="your-api-key",
            base_url="https://api.example.com/v1"
        )
        
        # Extract fields
        result = client.mapper.extract(pdf_path="s3://bucket/file.pdf")
        
        # Map fields
        result = client.mapper.map(
            pdf_path="s3://bucket/file.pdf",
            mapper_type="ensemble"
        )
        ```
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "http://localhost:8000",
        timeout: float = 300.0,
        **kwargs
    ):
        """
        Initialize PDF Mapper client.
        
        Args:
            api_key: API key for authentication
            base_url: Base URL of the API
            timeout: Request timeout in seconds
            **kwargs: Additional httpx client options
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        
        # Create HTTP client
        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            headers={
                "X-API-Key": self.api_key,
                "Content-Type": "application/json",
            },
            **kwargs
        )
        
        # Initialize resources
        self.mapper = MapperResource(self)
    
    def close(self):
        """Close the HTTP client."""
        self.client.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def _request(
        self,
        method: str,
        path: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make an HTTP request.
        
        Args:
            method: HTTP method
            path: API path
            **kwargs: Additional request options
            
        Returns:
            Response data
            
        Raises:
            httpx.HTTPError: If request fails
        """
        response = self.client.request(method, path, **kwargs)
        response.raise_for_status()
        return response.json()
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check API health.
        
        Returns:
            Health status
        """
        return self._request("GET", "/health")

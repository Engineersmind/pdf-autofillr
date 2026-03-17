"""
PDF Autofiller SDK - Synchronous Client

Simple HTTP client for calling the PDF Autofiller Mapper API.
Works with both local Docker deployments and remote cloud deployments.
"""

import requests
from typing import Optional, Dict, Any
from .exceptions import APIError, ValidationError, TimeoutError, ConnectionError


class PDFAutofillerClient:
    """
    Synchronous client for PDF Autofiller Mapper API.
    
    Usage:
        # Local Docker deployment
        client = PDFAutofillerClient(base_url="http://localhost:8000")
        
        # Remote deployment
        client = PDFAutofillerClient(
            base_url="https://your-api.example.com",
            api_key="your-api-key"  # If authentication is enabled
        )
        
        # Run full pipeline
        result = client.make_embed_file(
            user_id=553,
            session_id="abc-123",
            pdf_doc_id=990,
            use_second_mapper=True
        )
        
        print(f"Embedded PDF: {result['output_paths']['embedded_pdf']}")
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        timeout: int = 300  # 5 minutes default
    ):
        """
        Initialize the client.
        
        Args:
            base_url: Base URL of the API (e.g., http://localhost:8000)
            api_key: Optional API key for authentication (future)
            timeout: Request timeout in seconds (default: 300)
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()
        
        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'pdf-autofiller-sdk/0.1.0'
        })
        
        if api_key:
            self.session.headers['Authorization'] = f'Bearer {api_key}'
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make HTTP request to API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments for requests
            
        Returns:
            Response JSON as dictionary
            
        Raises:
            APIError: If API returns error response
            TimeoutError: If request times out
            ConnectionError: If cannot connect to API
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(
                method,
                url,
                timeout=kwargs.pop('timeout', self.timeout),
                **kwargs
            )
            
            # Handle error responses
            if response.status_code >= 400:
                try:
                    error_data = response.json()
                    error_msg = error_data.get('detail', error_data.get('error', 'Unknown error'))
                except:
                    error_msg = response.text or f"HTTP {response.status_code}"
                
                raise APIError(
                    f"API error: {error_msg}",
                    status_code=response.status_code,
                    response=response.json() if response.content else None
                )
            
            return response.json()
            
        except requests.exceptions.Timeout as e:
            raise TimeoutError(f"Request timed out after {self.timeout}s: {e}")
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"Cannot connect to API at {url}: {e}")
        except APIError:
            raise
        except Exception as e:
            raise APIError(f"Unexpected error: {e}")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check if API is healthy.
        
        Returns:
            Health status response
        """
        return self._request('GET', '/health')
    
    def make_embed_file(
        self,
        user_id: int,
        session_id: str,
        pdf_doc_id: int,
        investor_type: str = "individual",
        use_second_mapper: bool = False,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Run full pipeline: Extract → Map → Embed.
        
        Creates an embedded PDF ready to be filled with data.
        
        Args:
            user_id: User ID
            session_id: Session ID for tracking
            pdf_doc_id: PDF document ID
            investor_type: Type of investor ('individual', 'entity', etc.)
            use_second_mapper: Whether to use RAG mapper (dual mapper)
            timeout: Override default timeout for this request
            
        Returns:
            Result dictionary with output_paths and metadata
            
        Example:
            result = client.make_embed_file(
                user_id=553,
                session_id="abc-123",
                pdf_doc_id=990,
                use_second_mapper=True
            )
            
            # Access output files
            embedded_pdf = result['output_paths']['embedded_pdf']
            extracted_json = result['output_paths']['extracted_json']
            mapping_json = result['output_paths']['mapping_json']
        """
        payload = {
            'user_id': user_id,
            'session_id': session_id,
            'pdf_doc_id': pdf_doc_id,
            'investor_type': investor_type,
            'use_second_mapper': use_second_mapper
        }
        
        return self._request(
            'POST',
            '/make-embed-file',
            json=payload,
            timeout=timeout
        )
    
    def extract(
        self,
        user_id: int,
        session_id: str,
        pdf_doc_id: int,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Extract text and form fields from PDF.
        
        Args:
            user_id: User ID
            session_id: Session ID
            pdf_doc_id: PDF document ID
            timeout: Override default timeout
            
        Returns:
            Extraction result with output_file path
        """
        payload = {
            'user_id': user_id,
            'session_id': session_id,
            'pdf_doc_id': pdf_doc_id
        }
        
        return self._request(
            'POST',
            '/extract',
            json=payload,
            timeout=timeout
        )
    
    def map_fields(
        self,
        user_id: int,
        session_id: str,
        pdf_doc_id: int,
        investor_type: str = "individual",
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Map extracted fields to investor data schema.
        
        Args:
            user_id: User ID
            session_id: Session ID
            pdf_doc_id: PDF document ID
            investor_type: Type of investor
            timeout: Override default timeout
            
        Returns:
            Mapping result with output_file path
        """
        payload = {
            'user_id': user_id,
            'session_id': session_id,
            'pdf_doc_id': pdf_doc_id,
            'investor_type': investor_type
        }
        
        return self._request(
            'POST',
            '/map',
            json=payload,
            timeout=timeout
        )
    
    def embed(
        self,
        user_id: int,
        session_id: str,
        pdf_doc_id: int,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Embed field mappings into PDF form fields.
        
        Args:
            user_id: User ID
            session_id: Session ID
            pdf_doc_id: PDF document ID
            timeout: Override default timeout
            
        Returns:
            Embed result with output_file path
        """
        payload = {
            'user_id': user_id,
            'session_id': session_id,
            'pdf_doc_id': pdf_doc_id
        }
        
        return self._request(
            'POST',
            '/embed',
            json=payload,
            timeout=timeout
        )
    
    def fill(
        self,
        user_id: int,
        session_id: str,
        pdf_doc_id: int,
        data: Dict[str, Any],
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Fill PDF with provided data.
        
        Args:
            user_id: User ID
            session_id: Session ID
            pdf_doc_id: PDF document ID
            data: Data to fill into PDF fields
            timeout: Override default timeout
            
        Returns:
            Fill result with output_file path
        """
        payload = {
            'user_id': user_id,
            'session_id': session_id,
            'pdf_doc_id': pdf_doc_id,
            'data': data
        }
        
        return self._request(
            'POST',
            '/fill',
            json=payload,
            timeout=timeout
        )
    
    def close(self):
        """Close the session."""
        self.session.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


class AsyncPDFAutofillerClient:
    """
    Async client for PDF Autofiller Mapper API.
    
    Usage:
        import asyncio
        
        async def main():
            async with AsyncPDFAutofillerClient() as client:
                result = await client.make_embed_file(
                    user_id=553,
                    session_id="abc-123",
                    pdf_doc_id=990
                )
                print(result)
        
        asyncio.run(main())
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        timeout: int = 300
    ):
        """Initialize async client (requires aiohttp)."""
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self._session = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        import aiohttp
        
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'pdf-autofiller-sdk/0.1.0'
        }
        
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self._session = aiohttp.ClientSession(
            headers=headers,
            timeout=timeout
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._session:
            await self._session.close()
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make async HTTP request."""
        if not self._session:
            raise RuntimeError("Client must be used as async context manager")
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with self._session.request(method, url, **kwargs) as response:
                if response.status >= 400:
                    error_data = await response.json() if response.content_type == 'application/json' else {}
                    error_msg = error_data.get('detail', error_data.get('error', 'Unknown error'))
                    raise APIError(
                        f"API error: {error_msg}",
                        status_code=response.status,
                        response=error_data
                    )
                
                return await response.json()
        except Exception as e:
            if isinstance(e, APIError):
                raise
            raise APIError(f"Request failed: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check API health."""
        return await self._request('GET', '/health')
    
    async def make_embed_file(
        self,
        user_id: int,
        session_id: str,
        pdf_doc_id: int,
        investor_type: str = "individual",
        use_second_mapper: bool = False
    ) -> Dict[str, Any]:
        """Async version of make_embed_file."""
        payload = {
            'user_id': user_id,
            'session_id': session_id,
            'pdf_doc_id': pdf_doc_id,
            'investor_type': investor_type,
            'use_second_mapper': use_second_mapper
        }
        
        return await self._request('POST', '/make-embed-file', json=payload)
    
    # Add other async methods as needed...

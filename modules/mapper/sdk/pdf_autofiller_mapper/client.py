"""
PDF Mapper HTTP API Client

PDFMapperClient talks to a running mapper server over HTTP.
All httpx transport errors are translated into SDK exception types so callers
only need to handle ``PDFMapperError`` subclasses.

Quick start::

    from pdf_autofiller_mapper import PDFMapperClient

    with PDFMapperClient(base_url="http://localhost:8000") as client:
        result = client.mapper.make_embed_file(pdf_path="s3://bucket/form.pdf")
        print(result)
"""

import httpx
from typing import Optional, Dict, Any

from .resources.mapper import MapperResource
from .exceptions import APIError, ConnectionError, TimeoutError


class PDFMapperClient:
    """
    HTTP client for the PDF Mapper server.

    Connects to a running mapper HTTP server and exposes the same operations
    as the embedded ``PDFMapper`` SDK, but over the network.

    All network and HTTP errors are translated into ``PDFMapperError``
    subclasses so callers can catch ``from pdf_autofiller_mapper.exceptions import
    PDFMapperError`` to handle everything at once.

    Args:
        base_url: URL of the running mapper server
                  (default ``"http://localhost:8000"``).
        api_key:  Optional API key sent as ``X-API-Key`` header.
        timeout:  Request timeout in seconds (default 300).
                  LLM mapping calls can take 30–120 s; increase this if you
                  see ``TimeoutError`` on large forms.

    Example::

        with PDFMapperClient(base_url="http://my-server:8000") as client:
            if client.health_check()["status"] == "ok":
                result = client.mapper.make_embed_file(
                    pdf_path="s3://bucket/form.pdf"
                )
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        timeout: float = 300.0,
        **kwargs,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["X-API-Key"] = api_key

        self._http = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            headers=headers,
            **kwargs,
        )

        self.mapper = MapperResource(self)

    # ── Context manager ───────────────────────────────────────────────────────

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # ── Public helpers ────────────────────────────────────────────────────────

    def health_check(self) -> Dict[str, Any]:
        """
        Ping the server's ``/health`` endpoint.

        Returns:
            Dict with at least ``{"status": "ok"}``.

        Raises:
            ConnectionError: Server is unreachable.
            APIError:        Server returned an unexpected response.
        """
        return self._request("GET", "/health")

    # ── Internal request layer ────────────────────────────────────────────────

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """
        Execute an HTTP request and return the parsed JSON body.

        Translates httpx exceptions into SDK exception types:

        - ``httpx.ConnectError`` / ``httpx.NetworkError``  → ``ConnectionError``
        - ``httpx.TimeoutException``                        → ``TimeoutError``
        - ``httpx.HTTPStatusError`` (4xx / 5xx)            → ``APIError``

        Args:
            method: HTTP method (``"GET"``, ``"POST"``, …).
            path:   API path relative to ``base_url`` (e.g. ``"/health"``).
            **kwargs: Forwarded to ``httpx.Client.request``.

        Returns:
            Parsed JSON response body as a dict.

        Raises:
            ConnectionError: Could not connect to the server.
            TimeoutError:    Request timed out.
            APIError:        Server returned a 4xx or 5xx status code.
        """
        try:
            response = self._http.request(method, path, **kwargs)
            response.raise_for_status()
            return response.json()

        except httpx.TimeoutException as exc:
            raise TimeoutError(
                f"Request to {method} {path} timed out. "
                "Increase the timeout parameter on PDFMapperClient if this "
                "happens regularly on large forms."
            ) from exc

        except (httpx.ConnectError, httpx.NetworkError) as exc:
            raise ConnectionError(
                f"Could not reach the mapper server at {self.base_url!r}. "
                "Is the server running?"
            ) from exc

        except httpx.HTTPStatusError as exc:
            body = ""
            try:
                body = exc.response.text
            except Exception:
                pass
            raise APIError(
                f"Server returned {exc.response.status_code} for "
                f"{method} {path}",
                status_code=exc.response.status_code,
                response_body=body,
            ) from exc

        except httpx.HTTPError as exc:
            raise ConnectionError(
                f"HTTP error on {method} {path}: {exc}"
            ) from exc

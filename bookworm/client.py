"""HTTP client for Calibre API interactions."""

import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any, Dict, Optional, Tuple

import httpx


class CalibreClient:
    """HTTP client for interacting with Calibre content server API."""
    
    def __init__(self, base_url: str, library_id: str = None, debug: bool = False):
        """
        Initialize the Calibre client.
        
        Args:
            base_url: Base URL of the Calibre server (e.g., http://69.144.163.41:8080)
            library_id: Library ID (default: "books")
            debug: Enable verbose HTTP request/response logging (default: False)
        """
        self.base_url = base_url.rstrip('/')
        self.debug = debug
        self._client = httpx.Client(timeout=60.0)
        
        # If no library_id provided, fetch from OPDS (failfast - no defaults)
        if library_id is None:
            library_id = self.get_library_id_from_opds()
        self.library_id = library_id
    
    def get_library_id_from_opds(self) -> str:
        """
        Fetch the library ID from the /opds endpoint.
        
        Returns:
            Library ID string (e.g., "Calibre_Library")
            
        Raises:
            RuntimeError: If OPDS fetch fails or library ID not found
        """
        response = self._client.get(f"{self.base_url}/opds")
        
        if response.status_code != 200:
            raise RuntimeError(f"Failed to fetch OPDS: {response.status_code} - {response.text[:200]}")
        
        # Parse XML to find the library ID
        root = ET.fromstring(response.text)
        
        # Find the library entry
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        for entry in root.findall('.//atom:entry', ns):
            title_elem = entry.find('atom:title', ns)
            
            if title_elem is not None:
                title = title_elem.text
                
                if title.startswith("Library:"):
                    # Extract library ID from "Library: <id>" format
                    library_id = title.replace("Library:", "").strip()
                    if not library_id:
                        raise RuntimeError("Empty library ID from OPDS")
                    return library_id
        
        raise RuntimeError("No library entry found in OPDS feed")
    
    def list_libraries_from_opds(self) -> list:
        """
        Fetch all available libraries from the /opds endpoint.
        
        Returns:
            List of tuples (library_id, library_name)
        """
        response = self._client.get(f"{self.base_url}/opds")
        
        if response.status_code != 200:
            raise RuntimeError(f"Failed to fetch OPDS: {response.status_code}")
        
        root = ET.fromstring(response.text)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        libraries = []
        for entry in root.findall('.//atom:entry', ns):
            title_elem = entry.find('atom:title', ns)
            if title_elem is not None and title_elem.text and title_elem.text.startswith("Library:"):
                library_id = title_elem.text.replace("Library:", "").strip()
                libraries.append((library_id, library_id))
        
        return libraries
    
    def _print_request(self, method: str, url: str, headers: Dict[str, str] = None, body: str = None) -> None:
        """Print HTTP request details."""
        if not self.debug:
            return
        print(f"\n>>> REQUEST: {method} {url}")
        if headers:
            print(">>> Headers:")
            for key, value in headers.items():
                print(f">>>   {key}: {value}")
        if body:
            print(f">>> Body:")
            print(f">>>   {body}")
        print()
    
    def _print_response(self, status_code: int, headers: Dict[str, str], body: str = None) -> None:
        """Print HTTP response details."""
        if not self.debug:
            return
        print(f"<<< RESPONSE: {status_code}")
        print("<<< Headers:")
        for key, value in headers.items():
            print(f"<<<   {key}: {value}")
        if body:
            # Truncate large responses for readability
            if len(body) > 2000:
                print(f"<<< Body (truncated):")
                print(f"<<<   {body[:2000]}...")
            else:
                print(f"<<< Body:")
                print(f"<<<   {body}")
        print()
    
    def _get(self, path: str, params: Dict[str, Any] = None) -> Tuple[int, Dict[str, str], str]:
        """
        Make a GET request.
        
        Args:
            path: URL path
            params: Query parameters
            
        Returns:
            Tuple of (status_code, headers, body)
        """
        url = f"{self.base_url}{path}"
        if params:
            query_string = urllib.parse.urlencode(params)
            url = f"{url}?{query_string}"
        
        headers = {"Accept": "*/*"}
        self._print_request("GET", url, headers)
        
        response = self._client.get(url, headers=headers)
        
        self._print_response(response.status_code, dict(response.headers), response.text)
        
        return response.status_code, dict(response.headers), response.text
    
    def _post(self, path: str, json: Dict[str, Any]) -> Tuple[int, Dict[str, str], str]:
        """
        Make a POST request with JSON body.
        
        Args:
            path: URL path
            json: JSON body
            
        Returns:
            Tuple of (status_code, headers, body)
        """
        url = f"{self.base_url}{path}"
        
        headers = {
            "Accept": "*/*",
            "Content-Type": "application/json"
        }
        self._print_request("POST", url, headers, json.dumps(json))
        
        response = self._client.post(url, headers=headers, json=json)
        
        self._print_response(response.status_code, dict(response.headers), response.text)
        
        return response.status_code, dict(response.headers), response.text
    
    def _download(self, path: str) -> Tuple[int, Dict[str, str], bytes]:
        """
        Make a GET request and return binary content.
        
        Args:
            path: URL path
            
        Returns:
            Tuple of (status_code, headers, content)
        """
        url = f"{self.base_url}{path}"
        
        headers = {"Accept": "*/*"}
        self._print_request("GET", url, headers)
        
        response = self._client.get(url, headers=headers)
        
        self._print_response(response.status_code, dict(response.headers))
        
        return response.status_code, dict(response.headers), response.content
    
    def get_books_init(self, search: str, sort: str = None, order: str = "desc") -> Dict[str, Any]:
        """
        Get initial book list with search query.
        
        Args:
            search: Search string
            sort: Sort field (optional)
            order: Sort order (asc/desc)
            
        Returns:
            Parsed JSON response
        """
        params = {
            "library_id": self.library_id,
            "search": search
        }
        
        if sort:
            params["sort"] = f"{sort}.{order}"
        
        status_code, headers, body = self._get("/interface-data/books-init", params)
        
        if status_code != 200:
            raise RuntimeError(f"Failed to get books init: {status_code} - {body[:500]}")
        
        import json
        return json.loads(body)
    
    def get_more_books(self, query: str, offset: int, sort: str = None, order: str = "desc", vl: str = "") -> Dict[str, Any]:
        """
        Get more books with pagination.
        
        Args:
            query: Search query
            offset: Offset for pagination
            sort: Sort field (optional)
            order: Sort order (asc/desc)
            vl: View list (optional, default "")
            
        Returns:
            Parsed JSON response
        """
        json_body = {
            "offset": offset,
            "query": query,
            "sort": sort,
            "sort_order": order,
            "vl": vl
        }
        
        status_code, headers, body = self._post("/interface-data/more-books", json_body)
        
        if status_code != 200:
            raise RuntimeError(f"Failed to get more books: {status_code} - {body[:500]}")
        
        import json
        return json.loads(body)
    
    def get_book_metadata(self, book_id: int) -> Dict[str, Any]:
        """
        Get metadata for a specific book.
        
        Args:
            book_id: Book ID
            
        Returns:
            Parsed JSON response
        """
        params = {"library_id": self.library_id}
        status_code, headers, body = self._get(f"/interface-data/book-metadata/{book_id}", params)
        
        if status_code != 200:
            raise RuntimeError(f"Failed to get book metadata: {status_code} - {body[:500]}")
        
        import json
        return json.loads(body)
    
    def download_book(self, format: str, book_id: int, title: str = None) -> Tuple[str, bytes]:
        """
        Download a book file.
        
        Args:
            format: Book format (e.g., "EPUB", "PDF")
            book_id: Book ID
            title: Book title for filename (optional)
            
        Returns:
            Tuple of (filename, content)
        """
        status_code, headers, content = self._download(f"/get/{format}/{book_id}/{self.library_id}")
        
        if status_code != 200:
            raise RuntimeError(f"Failed to download book: {status_code}")
        
        import re
        # Use title-based filename if provided
        if title:
            # Replace all non-alphanumeric characters with underscores
            safe_title = re.sub(r'[^a-zA-Z0-9]', '_', title)
            # Collapse multiple underscores into one
            safe_title = re.sub(r'_+', '_', safe_title)
            # Remove leading/trailing underscores
            safe_title = safe_title.strip('_')
            filename = f"{safe_title}.{format.lower()}"
        else:
            filename = f"book_{book_id}.{format.lower()}"
        
        return filename, content

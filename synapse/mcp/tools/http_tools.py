"""
HTTP Tools - Make HTTP requests to external APIs
Supports GET, POST, PUT, DELETE with various content types
"""
import os
import json
from typing import Dict, Any, Optional
from urllib.parse import urljoin


def http_get(url: str, headers: Dict[str, str] = None, params: Dict[str, str] = None) -> Dict[str, Any]:
    """
    Make an HTTP GET request
    
    Args:
        url: The URL to request
        headers: Optional headers dict
        params: Optional query parameters
    """
    try:
        import httpx
        
        with httpx.Client(timeout=30) as client:
            response = client.get(url, headers=headers, params=params)
            
            return _format_response(response)
            
    except ImportError:
        # Fallback to requests
        import requests
        response = requests.get(url, headers=headers, params=params, timeout=30)
        return _format_response_requests(response)
    except Exception as e:
        return {"success": False, "error": str(e)}


def http_post(url: str, data: Any = None, json_data: Dict = None, headers: Dict[str, str] = None) -> Dict[str, Any]:
    """
    Make an HTTP POST request
    
    Args:
        url: The URL to request
        data: Form data or raw data
        json_data: JSON data to send
        headers: Optional headers dict
    """
    try:
        import httpx
        
        with httpx.Client(timeout=30) as client:
            if json_data:
                response = client.post(url, json=json_data, headers=headers)
            else:
                response = client.post(url, data=data, headers=headers)
            
            return _format_response(response)
            
    except ImportError:
        import requests
        if json_data:
            response = requests.post(url, json=json_data, headers=headers, timeout=30)
        else:
            response = requests.post(url, data=data, headers=headers, timeout=30)
        return _format_response_requests(response)
    except Exception as e:
        return {"success": False, "error": str(e)}


def http_put(url: str, data: Any = None, json_data: Dict = None, headers: Dict[str, str] = None) -> Dict[str, Any]:
    """Make an HTTP PUT request"""
    try:
        import httpx
        
        with httpx.Client(timeout=30) as client:
            if json_data:
                response = client.put(url, json=json_data, headers=headers)
            else:
                response = client.put(url, data=data, headers=headers)
            
            return _format_response(response)
            
    except ImportError:
        import requests
        if json_data:
            response = requests.put(url, json=json_data, headers=headers, timeout=30)
        else:
            response = requests.put(url, data=data, headers=headers, timeout=30)
        return _format_response_requests(response)
    except Exception as e:
        return {"success": False, "error": str(e)}


def http_delete(url: str, headers: Dict[str, str] = None) -> Dict[str, Any]:
    """Make an HTTP DELETE request"""
    try:
        import httpx
        
        with httpx.Client(timeout=30) as client:
            response = client.delete(url, headers=headers)
            return _format_response(response)
            
    except ImportError:
        import requests
        response = requests.delete(url, headers=headers, timeout=30)
        return _format_response_requests(response)
    except Exception as e:
        return {"success": False, "error": str(e)}


def fetch_webpage(url: str, extract_text: bool = True) -> Dict[str, Any]:
    """
    Fetch a webpage and optionally extract text content
    
    Args:
        url: URL to fetch
        extract_text: If True, extract readable text from HTML
    """
    try:
        import httpx
        from bs4 import BeautifulSoup
        
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            response = client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            
            if not extract_text:
                return {
                    "success": True,
                    "url": str(response.url),
                    "status_code": response.status_code,
                    "html": response.text
                }
            
            # Parse HTML and extract text
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()
            
            # Get text
            text = soup.get_text(separator='\n', strip=True)
            
            # Get title
            title = soup.title.string if soup.title else None
            
            # Get links
            links = []
            for link in soup.find_all('a', href=True)[:20]:  # Limit to 20 links
                href = link['href']
                if href.startswith('http'):
                    links.append({"text": link.get_text(strip=True)[:50], "url": href})
            
            return {
                "success": True,
                "url": str(response.url),
                "title": title,
                "text": text[:10000],  # Limit text length
                "links": links
            }
            
    except ImportError as e:
        return {"success": False, "error": f"Required library not installed: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def download_file(url: str, save_path: str) -> Dict[str, Any]:
    """
    Download a file from URL
    
    Args:
        url: URL to download from
        save_path: Local path to save the file
    """
    try:
        import httpx
        
        save_path = os.path.expanduser(save_path)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        
        with httpx.Client(timeout=60, follow_redirects=True) as client:
            response = client.get(url)
            
            if response.status_code != 200:
                return {"success": False, "error": f"HTTP {response.status_code}"}
            
            with open(save_path, 'wb') as f:
                f.write(response.content)
            
            return {
                "success": True,
                "url": url,
                "saved_to": os.path.abspath(save_path),
                "size_bytes": len(response.content)
            }
            
    except ImportError:
        import requests
        save_path = os.path.expanduser(save_path)
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        response = requests.get(url, timeout=60, allow_redirects=True)
        if response.status_code != 200:
            return {"success": False, "error": f"HTTP {response.status_code}"}
        with open(save_path, 'wb') as f:
            f.write(response.content)
        return {
            "success": True,
            "url": url,
            "saved_to": os.path.abspath(save_path),
            "size_bytes": len(response.content)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _format_response(response) -> Dict[str, Any]:
    """Format httpx response"""
    try:
        json_data = response.json()
        body = json_data
    except:
        body = response.text[:5000]  # Limit text length
    
    return {
        "success": response.status_code < 400,
        "status_code": response.status_code,
        "headers": dict(response.headers),
        "body": body
    }


def _format_response_requests(response) -> Dict[str, Any]:
    """Format requests response"""
    try:
        json_data = response.json()
        body = json_data
    except:
        body = response.text[:5000]
    
    return {
        "success": response.status_code < 400,
        "status_code": response.status_code,
        "headers": dict(response.headers),
        "body": body
    }

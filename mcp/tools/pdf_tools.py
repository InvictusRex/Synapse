"""
PDF Tools - Read and process PDF files
"""
import os
from typing import Dict, Any, List


def read_pdf(filepath: str, pages: str = "all") -> Dict[str, Any]:
    """
    Read text content from a PDF file
    
    Args:
        filepath: Path to the PDF file
        pages: "all" or specific pages like "1,2,5" or "1-5"
    """
    try:
        filepath = os.path.expanduser(filepath)
        
        if not os.path.exists(filepath):
            return {"success": False, "error": f"File not found: {filepath}"}
        
        if not filepath.lower().endswith('.pdf'):
            return {"success": False, "error": "File is not a PDF"}
        
        # Try pdfplumber first (better for tables)
        try:
            import pdfplumber
            
            text_content = []
            page_texts = {}
            
            with pdfplumber.open(filepath) as pdf:
                total_pages = len(pdf.pages)
                pages_to_read = _parse_page_range(pages, total_pages)
                
                for page_num in pages_to_read:
                    if 0 <= page_num < total_pages:
                        page = pdf.pages[page_num]
                        text = page.extract_text() or ""
                        text_content.append(text)
                        page_texts[page_num + 1] = text
            
            return {
                "success": True,
                "filepath": filepath,
                "total_pages": total_pages,
                "pages_read": len(pages_to_read),
                "content": "\n\n--- Page Break ---\n\n".join(text_content),
                "pages": page_texts
            }
            
        except ImportError:
            pass
        
        # Fallback to PyPDF2
        try:
            from PyPDF2 import PdfReader
            
            reader = PdfReader(filepath)
            total_pages = len(reader.pages)
            pages_to_read = _parse_page_range(pages, total_pages)
            
            text_content = []
            page_texts = {}
            
            for page_num in pages_to_read:
                if 0 <= page_num < total_pages:
                    text = reader.pages[page_num].extract_text() or ""
                    text_content.append(text)
                    page_texts[page_num + 1] = text
            
            return {
                "success": True,
                "filepath": filepath,
                "total_pages": total_pages,
                "pages_read": len(pages_to_read),
                "content": "\n\n--- Page Break ---\n\n".join(text_content),
                "pages": page_texts
            }
            
        except ImportError:
            return {"success": False, "error": "No PDF library available. Install PyPDF2 or pdfplumber."}
            
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_pdf_info(filepath: str) -> Dict[str, Any]:
    """Get metadata and info about a PDF file"""
    try:
        filepath = os.path.expanduser(filepath)
        
        if not os.path.exists(filepath):
            return {"success": False, "error": f"File not found: {filepath}"}
        
        try:
            from PyPDF2 import PdfReader
            
            reader = PdfReader(filepath)
            info = reader.metadata
            
            return {
                "success": True,
                "filepath": filepath,
                "total_pages": len(reader.pages),
                "metadata": {
                    "title": info.title if info else None,
                    "author": info.author if info else None,
                    "subject": info.subject if info else None,
                    "creator": info.creator if info else None,
                    "producer": info.producer if info else None,
                    "creation_date": str(info.creation_date) if info and info.creation_date else None
                }
            }
        except ImportError:
            return {"success": False, "error": "PyPDF2 not installed"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}


def extract_pdf_tables(filepath: str, page_number: int = None) -> Dict[str, Any]:
    """Extract tables from a PDF file"""
    try:
        filepath = os.path.expanduser(filepath)
        
        if not os.path.exists(filepath):
            return {"success": False, "error": f"File not found: {filepath}"}
        
        try:
            import pdfplumber
            
            tables_data = []
            
            with pdfplumber.open(filepath) as pdf:
                pages_to_check = [page_number - 1] if page_number else range(len(pdf.pages))
                
                for page_num in pages_to_check:
                    if 0 <= page_num < len(pdf.pages):
                        page = pdf.pages[page_num]
                        tables = page.extract_tables()
                        
                        for idx, table in enumerate(tables):
                            tables_data.append({
                                "page": page_num + 1,
                                "table_index": idx,
                                "rows": len(table),
                                "data": table
                            })
            
            return {
                "success": True,
                "filepath": filepath,
                "tables_found": len(tables_data),
                "tables": tables_data
            }
            
        except ImportError:
            return {"success": False, "error": "pdfplumber not installed. Required for table extraction."}
            
    except Exception as e:
        return {"success": False, "error": str(e)}


def _parse_page_range(pages: str, total_pages: int) -> List[int]:
    """Parse page range string into list of page indices (0-based)"""
    if pages.lower() == "all":
        return list(range(total_pages))
    
    result = []
    parts = pages.replace(" ", "").split(",")
    
    for part in parts:
        if "-" in part:
            start, end = part.split("-")
            start = int(start) - 1
            end = int(end)
            result.extend(range(start, min(end, total_pages)))
        else:
            page = int(part) - 1
            if 0 <= page < total_pages:
                result.append(page)
    
    return sorted(set(result))

"""
Image Tools - Generate and process images
Uses free APIs for generation (no API key required)
"""
import os
import requests
from typing import Dict, Any
from urllib.parse import quote
from datetime import datetime


def generate_image(prompt: str, filename: str = None, width: int = 1024, height: int = 1024, save_dir: str = "./outputs") -> Dict[str, Any]:
    """
    Generate an image using AI (free, no API key needed)
    Uses Pollinations.ai free API
    
    Args:
        prompt: Description of the image to generate
        filename: Output filename (auto-generated if not provided)
        width: Image width (default 1024)
        height: Image height (default 1024)
        save_dir: Directory to save the image
    """
    try:
        # URL encode the prompt
        encoded_prompt = quote(prompt)
        
        # Pollinations.ai free API
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}"
        
        print(f"[Image] Generating: {prompt[:50]}...")
        
        # Download the image
        response = requests.get(url, timeout=60)
        
        if response.status_code != 200:
            return {"success": False, "error": f"API returned status {response.status_code}"}
        
        # Ensure directory exists
        os.makedirs(save_dir, exist_ok=True)
        
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_prompt = "".join(c if c.isalnum() else "_" for c in prompt[:30])
            filename = f"image_{safe_prompt}_{timestamp}.png"
        
        filepath = os.path.join(save_dir, filename)
        
        # Save the image
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        return {
            "success": True,
            "filepath": os.path.abspath(filepath),
            "prompt": prompt,
            "dimensions": f"{width}x{height}",
            "size_bytes": len(response.content)
        }
        
    except requests.Timeout:
        return {"success": False, "error": "Image generation timed out. Try again."}
    except Exception as e:
        return {"success": False, "error": str(e)}


def resize_image(input_path: str, output_path: str, width: int = None, height: int = None, maintain_aspect: bool = True) -> Dict[str, Any]:
    """Resize an image"""
    try:
        from PIL import Image
        
        input_path = os.path.expanduser(input_path)
        output_path = os.path.expanduser(output_path)
        
        if not os.path.exists(input_path):
            return {"success": False, "error": f"File not found: {input_path}"}
        
        img = Image.open(input_path)
        original_width, original_height = img.size
        
        if maintain_aspect:
            if width and not height:
                ratio = width / original_width
                height = int(original_height * ratio)
            elif height and not width:
                ratio = height / original_height
                width = int(original_width * ratio)
            elif width and height:
                # Fit within bounds while maintaining aspect ratio
                ratio = min(width / original_width, height / original_height)
                width = int(original_width * ratio)
                height = int(original_height * ratio)
        
        if not width or not height:
            return {"success": False, "error": "Must specify width and/or height"}
        
        resized = img.resize((width, height), Image.LANCZOS)
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        
        resized.save(output_path)
        
        return {
            "success": True,
            "input": input_path,
            "output": os.path.abspath(output_path),
            "original_size": f"{original_width}x{original_height}",
            "new_size": f"{width}x{height}"
        }
        
    except ImportError:
        return {"success": False, "error": "Pillow not installed"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def convert_image(input_path: str, output_path: str, quality: int = 95) -> Dict[str, Any]:
    """Convert image to a different format"""
    try:
        from PIL import Image
        
        input_path = os.path.expanduser(input_path)
        output_path = os.path.expanduser(output_path)
        
        if not os.path.exists(input_path):
            return {"success": False, "error": f"File not found: {input_path}"}
        
        img = Image.open(input_path)
        
        # Handle transparency for JPEG conversion
        output_ext = os.path.splitext(output_path)[1].lower()
        if output_ext in ['.jpg', '.jpeg'] and img.mode in ['RGBA', 'P']:
            img = img.convert('RGB')
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        
        img.save(output_path, quality=quality)
        
        return {
            "success": True,
            "input": input_path,
            "output": os.path.abspath(output_path),
            "format": output_ext
        }
        
    except ImportError:
        return {"success": False, "error": "Pillow not installed"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_image_info(filepath: str) -> Dict[str, Any]:
    """Get information about an image file"""
    try:
        from PIL import Image
        
        filepath = os.path.expanduser(filepath)
        
        if not os.path.exists(filepath):
            return {"success": False, "error": f"File not found: {filepath}"}
        
        img = Image.open(filepath)
        
        return {
            "success": True,
            "filepath": filepath,
            "format": img.format,
            "mode": img.mode,
            "width": img.width,
            "height": img.height,
            "size_bytes": os.path.getsize(filepath)
        }
        
    except ImportError:
        return {"success": False, "error": "Pillow not installed"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def create_thumbnail(input_path: str, output_path: str, size: int = 128) -> Dict[str, Any]:
    """Create a thumbnail of an image"""
    try:
        from PIL import Image
        
        input_path = os.path.expanduser(input_path)
        output_path = os.path.expanduser(output_path)
        
        if not os.path.exists(input_path):
            return {"success": False, "error": f"File not found: {input_path}"}
        
        img = Image.open(input_path)
        img.thumbnail((size, size), Image.LANCZOS)
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        
        img.save(output_path)
        
        return {
            "success": True,
            "input": input_path,
            "output": os.path.abspath(output_path),
            "thumbnail_size": f"{img.width}x{img.height}"
        }
        
    except ImportError:
        return {"success": False, "error": "Pillow not installed"}
    except Exception as e:
        return {"success": False, "error": str(e)}

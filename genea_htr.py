#!/usr/bin/env python3
"""
Genealogy Assistant AI Handwritten Text Recognition Tool - Genea.ca
Copyright (C) 2025

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
"""
Handwriting transcription script using multiple AI APIs (OpenAI, Claude, OpenRouter)
Processes JPEG, PNG, and PDF files, transcribes handwriting, and creates searchable PDFs.
"""

import os
import sys
import base64
import glob
from typing import List, Dict, Optional, Union
import json
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import re
import unicodedata
import logging

# Core libraries
from PIL import Image
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as ReportLabImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import tempfile

# PDF processing
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    fitz = None

# API libraries - optional imports with fallback handling
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    anthropic = None

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None

try:
    import google.generativeai as genai
    GOOGLE_GENAI_AVAILABLE = True
except ImportError:
    GOOGLE_GENAI_AVAILABLE = False
    genai = None


class APIProvider:
    """Base class for API providers."""
    
    def __init__(self, api_key: str, **kwargs):
        self.api_key = api_key
        self.kwargs = kwargs
        
    def create_client(self):
        """Create and return the API client."""
        raise NotImplementedError
        
    def make_request(self, client, messages: List[Dict], model: str, **kwargs) -> str:
        """Make a request to the API and return the response content."""
        raise NotImplementedError
        
    def format_messages(self, prompt: str, base64_image: str) -> List[Dict]:
        """Format messages for the specific API."""
        raise NotImplementedError


class OpenAIProvider(APIProvider):
    """OpenAI API provider."""
    
    def create_client(self):
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI library not available. Install with: pip install openai")
        return openai.OpenAI(api_key=self.api_key)
    
    def format_messages(self, prompt: str, base64_image: str) -> List[Dict]:
        return [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ]
    
    def make_request(self, client, messages: List[Dict], model: str, **kwargs) -> str:
        # Prepare parameters for OpenAI API
        api_params = {
            "model": model,
            "messages": messages,
            **kwargs
        }
        
        response = client.chat.completions.create(**api_params)
        return response.choices[0].message.content


class ClaudeProvider(APIProvider):
    """Anthropic Claude API provider."""
    
    def create_client(self):
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("Anthropic library not available. Install with: pip install anthropic")
        return anthropic.Anthropic(api_key=self.api_key)
    
    def format_messages(self, prompt: str, base64_image: str) -> List[Dict]:
        return [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": base64_image
                        }
                    }
                ]
            }
        ]
    
    def make_request(self, client, messages: List[Dict], model: str, **kwargs) -> str:
        # Map OpenAI-style parameters to Claude parameters
        claude_params = {
            "model": model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", kwargs.get("max_completion_tokens", 8000)),
        }
        
        # Add optional parameters if present
        if "temperature" in kwargs:
            claude_params["temperature"] = kwargs["temperature"]
        if "top_p" in kwargs:
            claude_params["top_p"] = kwargs["top_p"]
            
        response = client.messages.create(**claude_params)
        return response.content[0].text


class OpenRouterProvider(APIProvider):
    """OpenRouter API provider."""
    
    def create_client(self):
        if not REQUESTS_AVAILABLE:
            raise ImportError("Requests library not available. Install with: pip install requests")
        return None  # OpenRouter uses requests directly
    
    def format_messages(self, prompt: str, base64_image: str) -> List[Dict]:
        return [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ]
    
    def make_request(self, client, messages: List[Dict], model: str, **kwargs) -> str:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Prepare parameters for OpenRouter API
        data = {
            "model": model,
            "messages": messages,
            **kwargs
        }
        
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]


class GeminiProvider(APIProvider):
    """Google Gemini API provider."""
    
    def create_client(self):
        if not GOOGLE_GENAI_AVAILABLE:
            raise ImportError("Google GenerativeAI library not available. Install with: pip install google-generativeai")
        
        # Configure the API key
        genai.configure(api_key=self.api_key)
        return genai  # Return the configured module
    
    def format_messages(self, prompt: str, base64_image: str) -> List[Dict]:
        # Gemini uses a different format - we'll return the data we need for make_request
        # Convert base64 to PIL Image for Gemini
        import io
        import base64
        from PIL import Image
        
        image_data = base64.b64decode(base64_image)
        pil_image = Image.open(io.BytesIO(image_data))
        
        return [{"prompt": prompt, "image": pil_image}]
    
    def make_request(self, client, messages: List[Dict], model: str, **kwargs) -> str:
        # Extract the prompt and image from the formatted messages
        prompt = messages[0]["prompt"]
        image = messages[0]["image"]
        
        # Create the model
        try:
            model_instance = client.GenerativeModel(model)
        except Exception as e:
            raise ValueError(f"Error creating Gemini model '{model}': {e}")
        
        # Prepare generation config
        generation_config = {}
        
        # Map common parameters to Gemini equivalents
        if "temperature" in kwargs:
            generation_config["temperature"] = kwargs["temperature"]
        if "top_p" in kwargs:
            generation_config["top_p"] = kwargs["top_p"]
        if "max_tokens" in kwargs:
            generation_config["max_output_tokens"] = kwargs["max_tokens"]
        elif "max_completion_tokens" in kwargs:
            generation_config["max_output_tokens"] = kwargs["max_completion_tokens"]
        
        # Generate content
        try:
            response = model_instance.generate_content(
                [prompt, image],
                generation_config=generation_config if generation_config else None
            )
            
            # Check if the response was blocked
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                if hasattr(response.prompt_feedback, 'block_reason'):
                    raise ValueError(f"Content was blocked: {response.prompt_feedback.block_reason}")
            
            return response.text
            
        except Exception as e:
            # Handle common Gemini API errors
            error_msg = str(e)
            if "SAFETY" in error_msg or "blocked" in error_msg.lower():
                raise ValueError(f"Content blocked by Gemini safety filters: {error_msg}")
            elif "quota" in error_msg.lower() or "rate" in error_msg.lower():
                raise ValueError(f"Gemini API quota/rate limit exceeded: {error_msg}")
            else:
                raise ValueError(f"Gemini API error: {error_msg}")


class HandwritingOCR:
    def __init__(self, api_key: str, provider: str = "openai", output_dir: str = "output", max_workers: int = 1):
        """
        Initialize the HandwritingOCR processor.
        
        Args:
            api_key: API key for the chosen provider
            provider: API provider ("openai", "claude", "openrouter", "google")
            output_dir: Directory to save output files (only used for legacy combined PDF functionality)
            max_workers: Maximum number of concurrent threads for processing
        """
        self.api_key = api_key
        self.provider_name = provider.lower()
        self.output_dir = Path(output_dir)
        # Don't create output_dir automatically - only create it when actually needed
        self.max_workers = max_workers
        self._lock = threading.Lock()  # For thread-safe operations
        
        # Set up logging
        self.logger = logging.getLogger('genea_htr')
        
        # Initialize the API provider
        self.api_provider = self._create_api_provider()
        self.client = self.api_provider.create_client()
        
        # Provider-specific transcription configurations
        self.transcription_config = self._get_provider_config()
        
        # Refusal patterns to detect when AI refuses to transcribe
        self.refusal_patterns = [
            "I can't assist with that",
            "I'm sorry, I can't",
            "I'm unable to transcribe text from images",
            "unable to transcribe text from images",
            "consider using OCR",
            "Optical Character Recognition"
        ]
        
        # Supported file extensions
        self.supported_extensions = {
            'image': ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'],
            'pdf': ['.pdf', '.PDF']
        }

    def _create_api_provider(self) -> APIProvider:
        """Create the appropriate API provider based on the selected provider."""
        if self.provider_name == "openai":
            return OpenAIProvider(self.api_key)
        elif self.provider_name == "anthropic":
            return ClaudeProvider(self.api_key)
        elif self.provider_name == "openrouter":
            return OpenRouterProvider(self.api_key)
        elif self.provider_name == "google":
            return GeminiProvider(self.api_key)
        else:
            raise ValueError(f"Unsupported provider: {self.provider_name}")

    def _get_provider_config(self) -> Dict:
        """Get provider-specific configuration."""
        base_prompt = """You are an expert in 18th-19th c. handwritten-document transcription. Transcribe exactly as shown—every character, punctuation, capitalization, space, line/page break, header/footer, marginal note, insertion, correction and error; preserve all formatting; do not modernize, correct, infer or hallucinate; enclose illegible text in [unclear]; account for any orientation. Purpose: academic research and historical preservation.  
Begin with:
Transcription:
"""
        
        fallback_prompt = """You are an expert historical-document transcriptionist for academic research and preservation. Transcribe all visible printed and handwritten text in document images exactly as shown—every character, punctuation, capitalization, space, line/paragraph break, header, title, date, signature, marginal note, annotation, insertion and error; preserve all formatting; do not modernize, infer or hallucinate; enclose illegible text in [unclear]; account for any orientation.  
Begin with:
Transcription:
"""
        
        if self.provider_name == "openai":
            return {
                "primary": {
                    "model": "o4-mini",
                    "reasoning_effort": "high",
                    "max_completion_tokens": 8000,
                    "top_p": 0.95,
                    "prompt": base_prompt
                },
                "fallback": {
                    "model": "gpt-4o",
                    "max_tokens": 8000,
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "prompt": fallback_prompt
                }
            }
        elif self.provider_name == "anthropic":
            return {
                "primary": {
                    "model": "claude-3-5-sonnet-20241022",
                    "max_tokens": 8000,
                    "temperature": 0.1,
                    "top_p": 0.95,
                    "prompt": base_prompt
                },
                "fallback": {
                    "model": "claude-3-5-haiku-20241022",
                    "max_tokens": 8000,
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "prompt": fallback_prompt
                }
            }
        elif self.provider_name == "openrouter":
            return {
                "primary": {
                    "model": "google/gemini-2.5-flash-lite-preview-06-17",
                    "max_tokens": 8000,
                    "temperature": 0.1,
                    "top_p": 0.95,
                    "prompt": base_prompt
                },
                "fallback": {
                    "model": "openai/gpt-4o",
                    "max_tokens": 8000,
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "prompt": fallback_prompt
                }
            }
        elif self.provider_name == "google":
            return {
                "primary": {
                    "model": "gemini-2.5-flash-lite-preview-06-17",
                    "max_tokens": 8000,
                    "temperature": 0.1,
                    "top_p": 0.95,
                    "prompt": base_prompt
                },
                "fallback": {
                    "model": "gemini-2.0-flash-lite",
                    "max_tokens": 8000,
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "prompt": fallback_prompt
                }
            }
        else:
            raise ValueError(f"No configuration available for provider: {self.provider_name}")

    def clean_text_for_pdf(self, text: str) -> str:
        """
        Clean text to remove problematic characters that cause black squares in PDFs.
        
        Args:
            text: Raw text from AI transcription
            
        Returns:
            Cleaned text safe for PDF rendering
        """
        if not text:
            return text
            
        # Step 1: Normalize Unicode characters
        # Convert to NFD (decomposed) form, then back to NFC (composed) form
        text = unicodedata.normalize('NFD', text)
        text = unicodedata.normalize('NFC', text)
        
        # Step 2: Remove or replace problematic Unicode categories
        cleaned_chars = []
        for char in text:
            # Get Unicode category
            category = unicodedata.category(char)
            
            # Keep most printable characters
            if category.startswith('L'):  # Letters
                cleaned_chars.append(char)
            elif category.startswith('N'):  # Numbers
                cleaned_chars.append(char)
            elif category.startswith('P'):  # Punctuation
                cleaned_chars.append(char)
            elif category.startswith('S') and char in '°±×÷§¶†‡•‰‱′″‴‵‶‷‸‹›«»':  # Some safe symbols
                cleaned_chars.append(char)
            elif category == 'Zs':  # Space separators
                cleaned_chars.append(char)
            elif char in '\n\r\t':  # Basic whitespace
                cleaned_chars.append(char)
            elif category.startswith('M'):  # Marks (combining characters)
                # Skip combining characters that might cause issues
                continue
            elif category.startswith('C'):  # Control characters
                # Replace control characters with space or remove them
                if char in '\n\r\t':
                    cleaned_chars.append(char)
                else:
                    continue  # Skip other control characters
            else:
                # For any other character, try to keep safe ones
                # Replace potentially problematic characters with a safe alternative
                if ord(char) < 32:  # Control characters
                    continue
                elif ord(char) > 65535:  # Characters outside Basic Multilingual Plane
                    cleaned_chars.append('?')  # Replace with question mark
                else:
                    cleaned_chars.append(char)
        
        cleaned_text = ''.join(cleaned_chars)
        
        # Step 3: Remove any remaining problematic patterns
        # Remove zero-width characters and other invisible characters
        cleaned_text = re.sub(r'[\u200b-\u200f\u2028-\u202f\u205f-\u206f\ufeff]', '', cleaned_text)
        
        # Step 4: Handle common Unicode characters that cause issues
        # Replace smart quotes and similar characters with ASCII equivalents
        unicode_replacements = {
            '\u2018': "'",  # Left single quotation mark
            '\u2019': "'",  # Right single quotation mark (apostrophe)
            '\u201C': '"',  # Left double quotation mark
            '\u201D': '"',  # Right double quotation mark
            '\u2013': '-',  # En dash
            '\u2014': '--', # Em dash
            '\u2026': '...', # Horizontal ellipsis
            '\u00A0': ' ',  # Non-breaking space
        }
        
        for unicode_char, replacement in unicode_replacements.items():
            cleaned_text = cleaned_text.replace(unicode_char, replacement)
        
        # Step 5: Final encoding check - only replace truly problematic characters
        final_chars = []
        for char in cleaned_text:
            try:
                # Test if character can be encoded in latin-1
                char.encode('latin-1')
                final_chars.append(char)
            except UnicodeEncodeError:
                # Only replace characters that truly can't be encoded
                # Skip rather than replace with ? to avoid unwanted question marks
                if ord(char) > 255:  # Characters outside latin-1 range
                    continue  # Skip the character entirely
                else:
                    final_chars.append(char)
        
        return ''.join(final_chars)

    def is_supported_file(self, file_path: str) -> bool:
        """Check if the file is a supported format."""
        path = Path(file_path)
        ext = path.suffix.lower()
        
        # Check if it's an image file
        if ext in [e.lower() for e in self.supported_extensions['image']]:
            return True
        
        # Check if it's a PDF file
        if ext in [e.lower() for e in self.supported_extensions['pdf']]:
            return True
            
        return False
    
    def extract_images_from_pdf(self, pdf_path: str) -> List[str]:
        """
        Extract pages from PDF as images and save them as temporary files.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of paths to temporary image files created from PDF pages
        """
        if not PYMUPDF_AVAILABLE:
            raise ImportError("PyMuPDF is required for PDF processing. Install with: pip install PyMuPDF")
        
        temp_image_paths = []
        
        try:
            # Open the PDF
            pdf_document = fitz.open(pdf_path)
            
            self.logger.info(f"Processing PDF: {os.path.basename(pdf_path)} ({pdf_document.page_count} pages)")
            
            for page_num in range(pdf_document.page_count):
                page = pdf_document[page_num]
                
                # Convert page to image (300 DPI for good quality)
                mat = fitz.Matrix(300/72, 300/72)  # 300 DPI scaling matrix
                pix = page.get_pixmap(matrix=mat)
                
                # Create temporary file for this page
                with tempfile.NamedTemporaryFile(suffix=f'_page_{page_num + 1}.png', delete=False) as temp_file:
                    temp_path = temp_file.name
                    
                # Save the image
                pix.save(temp_path)
                temp_image_paths.append(temp_path)
                
                self.logger.info(f"Extracted page {page_num + 1} from PDF to {os.path.basename(temp_path)}")
            
            pdf_document.close()
            
        except Exception as e:
            # Clean up any temporary files created before the error
            for temp_path in temp_image_paths:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
            self.logger.error(f"Error processing PDF {pdf_path}: {e}")
            raise
        
        return temp_image_paths

    def encode_image(self, image_path: str) -> str:
        """Encode image to base64 string for AI APIs."""
        try:
            # Get the file extension to determine the original format
            file_ext = Path(image_path).suffix.lower()
            
            # First, check if the image needs conversion
            with Image.open(image_path) as img:
                # If image is not RGB, convert it
                if img.mode != 'RGB':
                    self.logger.info(f"Converting {os.path.basename(image_path)} from {img.mode} to RGB...")
                    rgb_img = img.convert('RGB')
                    
                    # Save to bytes buffer as JPEG for better API compatibility
                    import io
                    buffer = io.BytesIO()
                    rgb_img.save(buffer, format='JPEG', quality=95)
                    image_data = buffer.getvalue()
                    
                    return base64.b64encode(image_data).decode('utf-8')
                else:
                    # For PNG files, convert to JPEG for better API compatibility and smaller size
                    if file_ext in ['.png']:
                        self.logger.info(f"Converting PNG {os.path.basename(image_path)} to JPEG for API compatibility...")
                        import io
                        buffer = io.BytesIO()
                        img.save(buffer, format='JPEG', quality=95)
                        image_data = buffer.getvalue()
                        return base64.b64encode(image_data).decode('utf-8')
                    else:
                        # Image is already RGB JPEG, use original file
                        with open(image_path, "rb") as image_file:
                            return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            self.logger.error(f"Error processing image {image_path}: {e}")
            # Fallback to original method
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')

    def _make_transcription_request(self, base64_image: str, config_key: str = "primary") -> str:
        """
        Make a transcription request using the specified configuration.
        
        Args:
            base64_image: Base64 encoded image
            config_key: Configuration key ("primary" or "fallback")
            
        Returns:
            Raw response from the API
        """
        config = self.transcription_config[config_key]
        
        # Format messages using the provider-specific format
        messages = self.api_provider.format_messages(config["prompt"], base64_image)
        
        # Extract parameters (excluding model and prompt)
        api_params = {}
        for key, value in config.items():
            if key not in ["model", "prompt"]:
                api_params[key] = value
        
        # Make the request using the provider
        return self.api_provider.make_request(
            self.client, 
            messages, 
            config["model"], 
            **api_params
        )

    def transcribe_image(self, image_path: str, max_retries: int = 3) -> str:
        """
        Transcribe handwriting from an image using the configured AI provider.
        
        Args:
            image_path: Path to the JPEG image
            max_retries: Maximum number of retry attempts for empty responses
            
        Returns:
            Transcribed text
        """
        # Encode the image once
        base64_image = self.encode_image(image_path)
        
        # Try primary transcription method first
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    self.logger.info(f"Retry attempt {attempt} for {os.path.basename(image_path)}...")
                else:
                    self.logger.info(f"Processing {os.path.basename(image_path)}...")
                
                # Make API call using primary configuration
                full_response = self._make_transcription_request(base64_image, "primary")
                
                # Check if the AI refused to transcribe
                if any(pattern in full_response for pattern in self.refusal_patterns):
                    self.logger.info(f"AI refused initial request for {os.path.basename(image_path)}, trying fallback...")
                    return self.transcribe_image_fallback(base64_image, image_path, max_retries)
                
                # Look for "Transcription:" and extract the text after it
                if "Transcription:" in full_response:
                    transcription = full_response.split("Transcription:", 1)[1].strip()
                else:
                    transcription = full_response.strip()
                
                # Check if transcription is empty or just whitespace
                if not transcription or transcription.isspace():
                    if attempt < max_retries:
                        self.logger.warning(f"Empty transcription received for {os.path.basename(image_path)}, retrying...")
                        continue
                    else:
                        self.logger.warning(f"Empty transcription after {max_retries} retries for {os.path.basename(image_path)}, trying fallback...")
                        return self.transcribe_image_fallback(base64_image, image_path, max_retries)
                
                self.logger.info(f"Successfully transcribed {os.path.basename(image_path)}")
                return transcription
                
            except Exception as e:
                if attempt < max_retries:
                    self.logger.warning(f"Error on attempt {attempt + 1} for {os.path.basename(image_path)}: {str(e)}, retrying...")
                    continue
                else:
                    self.logger.error(f"Error processing {os.path.basename(image_path)} after {max_retries} retries: {str(e)}")
                    return f"[Error: Could not transcribe {os.path.basename(image_path)} after {max_retries} attempts]"
        
        return f"[Error: Unexpected end of retry loop for {os.path.basename(image_path)}]"
    
    def transcribe_image_fallback(self, base64_image: str, image_path: str, max_retries: int = 3) -> str:
        """
        Fallback transcription method using alternative prompt and configuration.
        Called when primary method fails due to refusal or empty responses.
        
        Args:
            base64_image: Base64 encoded image
            image_path: Path to the image file (for logging)
            max_retries: Maximum number of retry attempts
            
        Returns:
            Transcribed text or error message
        """
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    self.logger.info(f"Fallback retry attempt {attempt} for {os.path.basename(image_path)}")
                else:
                    self.logger.info(f"Using fallback method for {os.path.basename(image_path)}")
                
                # Make API call using fallback configuration
                full_response = self._make_transcription_request(base64_image, "fallback")
                
                # Check if still refused
                if any(pattern in full_response for pattern in self.refusal_patterns):
                    self.logger.warning(f"AI refused fallback prompt for {os.path.basename(image_path)}")
                    return f"[Unable to transcribe: Content flagged by AI safety filters - {os.path.basename(image_path)}]"
                
                # Extract transcription
                if "Transcription:" in full_response:
                    transcription = full_response.split("Transcription:", 1)[1].strip()
                else:
                    transcription = full_response.strip()
                
                # Check if transcription is empty or just whitespace
                if not transcription or transcription.isspace():
                    if attempt < max_retries:
                        self.logger.warning(f"Empty transcription from fallback for {os.path.basename(image_path)}, retrying...")
                        continue
                    else:
                        self.logger.warning(f"Empty transcription from fallback after {max_retries} retries for {os.path.basename(image_path)}")
                        return f"[Empty: No text transcribed with fallback after {max_retries} attempts - {os.path.basename(image_path)}]"
                
                self.logger.info(f"Successfully transcribed {os.path.basename(image_path)} with fallback method")
                return transcription
                
            except Exception as e:
                if attempt < max_retries:
                    self.logger.warning(f"Error on fallback attempt {attempt + 1} for {os.path.basename(image_path)}: {str(e)}, retrying...")
                    continue
                else:
                    self.logger.error(f"Error with fallback for {os.path.basename(image_path)} after {max_retries} retries: {str(e)}")
                    return f"[Error: Could not transcribe with fallback after {max_retries} attempts - {os.path.basename(image_path)}]"
        
        return f"[Error: Unexpected end of fallback retry loop for {os.path.basename(image_path)}]"
    
    def create_individual_pdf(self, image_path: str, transcription: str, output_filename: str) -> str:
        """
        Create a searchable PDF for a single image with full resolution.
        First page(s): Transcription on standard 8.5x11 page with margins
        Last page: Image at full size (300 DPI equivalent) with no margins
        
        Args:
            image_path: Path to the image file
            transcription: Transcribed text
            output_filename: Output PDF filename
            
        Returns:
            Path to the created PDF
        """
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import inch
        from reportlab.platypus import PageBreak, Paragraph
        
        # Create PDFs folder in the same directory as the source image
        image_dir = Path(image_path).parent
        pdf_dir = image_dir / "PDFs"
        pdf_dir.mkdir(exist_ok=True)
        
        pdf_path = pdf_dir / output_filename
        
        try:
            # Get image dimensions for later use
            with Image.open(image_path) as img:
                img_width_px, img_height_px = img.size
                
                # Convert pixels to points at 300 DPI (1 inch = 72 points, 300 pixels = 1 inch)
                # So 1 pixel = 72/300 points = 0.24 points
                points_per_pixel = 72.0 / 300.0
                img_width_pts = img_width_px * points_per_pixel
                img_height_pts = img_height_px * points_per_pixel
                
                # Start PDF with standard letter size for transcription
                from reportlab.lib.pagesizes import letter
                c = canvas.Canvas(str(pdf_path), pagesize=letter)
                
                # Set up styles for transcription page
                styles = getSampleStyleSheet()
                
                # Create a frame for the transcription content with margins
                from reportlab.platypus import Frame, BaseDocTemplate
                margin = 72  # 1 inch margins
                frame_width = letter[0] - 2 * margin
                frame_height = letter[1] - 2 * margin
                
                # Clean the transcription text to prevent black squares in PDF
                cleaned_transcription = self.clean_text_for_pdf(transcription)
                
                # Page 1 (and potentially more): Transcription pages
                # Draw transcription content manually
                c.setFont("Helvetica-Bold", 14)
                c.drawString(margin, letter[1] - margin - 20, f"Transcription: {os.path.basename(image_path)}")
                
                # Calculate available space for text (leave room for footer)
                footer_height = 80  # Space reserved for footer
                available_height = letter[1] - margin - 60 - footer_height
                
                # Draw transcription text with proper flow management
                c.setFont("Helvetica", 11)
                y_position = letter[1] - margin - 60
                line_height = 14
                
                # Split transcription into lines and handle line breaks
                lines = cleaned_transcription.split('\n')
                for line in lines:
                    # Check if we have space for this line
                    if y_position - line_height < footer_height + 20:  # 20 points buffer above footer
                        # Start a new page if we're running out of space
                        c.showPage()
                        c.setPageSize(letter)
                        c.setFont("Helvetica", 11)
                        y_position = letter[1] - margin - 20  # Start closer to top on continuation pages
                    
                    # Handle long lines by wrapping them
                    if len(line) > 80:  # Approximate character limit per line
                        words = line.split(' ')
                        current_line = ""
                        for word in words:
                            if len(current_line + word) < 80:
                                current_line += word + " "
                            else:
                                if current_line:
                                    # Check space before drawing
                                    if y_position - line_height < footer_height + 20:
                                        c.showPage()
                                        c.setPageSize(letter)
                                        c.setFont("Helvetica", 11)
                                        y_position = letter[1] - margin - 20  # Start closer to top on continuation pages
                                    
                                    c.drawString(margin, y_position, current_line.strip())
                                    y_position -= line_height
                                current_line = word + " "
                        if current_line:
                            # Check space before drawing
                            if y_position - line_height < footer_height + 20:
                                c.showPage()
                                c.setPageSize(letter)
                                c.setFont("Helvetica", 11)
                                y_position = letter[1] - margin - 20  # Start closer to top on continuation pages
                            
                            c.drawString(margin, y_position, current_line.strip())
                            y_position -= line_height
                    else:
                        # Check space before drawing
                        if y_position - line_height < footer_height + 20:
                            c.showPage()
                            c.setPageSize(letter)
                            c.setFont("Helvetica", 11)
                            y_position = letter[1] - margin - 20  # Start closer to top on continuation pages
                        
                        c.drawString(margin, y_position, line)
                        y_position -= line_height
                
                # Add footer at bottom of current transcription page
                c.setFont("Helvetica", 9)
                c.setFillGray(0.5)
                current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                provider_info = f"{self.provider_name.upper()}: {self.transcription_config['primary']['model']}"
                footer_text = f"Generated by {provider_info} on {current_date}"
                footer_width = c.stringWidth(footer_text, "Helvetica", 9)
                c.drawString((letter[0] - footer_width) / 2, 50, footer_text)
                
                # End transcription page(s) and start new page for image
                c.showPage()
                
                # Last page: Image at full size with no margins
                c.setPageSize((img_width_pts, img_height_pts))  # Switch to custom image size
                c.drawImage(image_path, 0, 0, width=img_width_pts, height=img_height_pts)
                
                # Save the PDF
                c.save()
                
                self.logger.info(f"Created PDF: {os.path.basename(pdf_path)}")
                return str(pdf_path)
                
        except Exception as e:
            self.logger.error(f"Error creating PDF for {os.path.basename(image_path)}: {e}")
            # Fallback: create a simple PDF with error message
            try:
                c = canvas.Canvas(str(pdf_path), pagesize=letter)
                c.setFont("Helvetica", 12)
                c.drawString(72, letter[1] - 72, f"Error creating PDF for {os.path.basename(image_path)}")
                c.drawString(72, letter[1] - 100, f"Error: {str(e)}")
                c.save()
                return str(pdf_path)
            except:
                raise

    def _process_single_file(self, image_info: Dict, page_number: int, total_files: int) -> Dict:
        """
        Process a single image file (for use in concurrent processing).
        
        Args:
            image_info: Dictionary containing file information (path, original_file, is_pdf_page, etc.)
            page_number: Page number for this file
            total_files: Total number of files being processed
            
        Returns:
            Dictionary with processing result for this file
        """
        image_path = image_info['path']
        display_name = image_info['display_name']
        original_file = image_info['original_file']
        is_pdf_page = image_info['is_pdf_page']
        
        # Thread-safe logging
        self.logger.info(f"Processing file {page_number}/{total_files}: {display_name}")
        
        try:
            transcription = self.transcribe_image(image_path)
            
            # Create individual PDF for this image
            if is_pdf_page:
                # For PDF pages, include page info in filename
                original_name = Path(original_file).stem
                pdf_page_num = image_info['page_number']
                pdf_filename = f"{original_name}_page_{pdf_page_num}.pdf"
            else:
                # For regular images, use original filename
                pdf_filename = f"{Path(original_file).stem}.pdf"
            
            # Use original file directory for PDF location (not temp file directory)
            source_dir = Path(original_file).parent
            pdf_dir = source_dir / "PDFs"
            pdf_dir.mkdir(exist_ok=True)
            pdf_path = str(pdf_dir / pdf_filename)
            
            # Create the PDF using the processed image
            pdf_path = self.create_individual_pdf(image_path, transcription, pdf_filename)
            
            self.logger.info(f"Completed file {page_number}/{total_files}: {display_name}")
            
            return {
                "image_path": image_path,
                "original_file": original_file,
                "filename": display_name,
                "transcription": transcription,
                "pdf_path": pdf_path,
                "page_number": page_number,
                "is_pdf_page": is_pdf_page,
                "status": "success"
            }
            
        except Exception as e:
            self.logger.error(f"Error processing file {page_number}/{total_files}: {display_name} - {str(e)}")
            
            return {
                "image_path": image_path,
                "original_file": original_file,
                "filename": display_name,
                "transcription": f"[Error: {str(e)}]",
                "pdf_path": None,
                "page_number": page_number,
                "is_pdf_page": is_pdf_page,
                "status": "error",
                "error": str(e)
            }

    def process_batch(self, input_dir: str, output_filename: str = "transcribed_documents.pdf") -> Dict:
        """
        Process a batch of image and PDF files and create individual searchable PDFs.
        
        Args:
            input_dir: Directory containing image and PDF files
            output_filename: Base name for output files (not used for individual PDFs)
            
        Returns:
            Dictionary with processing results
        """
        # Find all supported files
        supported_patterns = ["*.jpg", "*.jpeg", "*.JPG", "*.JPEG", "*.png", "*.PNG", "*.pdf", "*.PDF"]
        input_files = []
        
        for pattern in supported_patterns:
            input_files.extend(glob.glob(os.path.join(input_dir, pattern)))
        
        if not input_files:
            self.logger.warning(f"No supported files found in {input_dir}")
            return {"status": "error", "message": "No supported files (JPEG, PNG, PDF) found"}
        
        input_files.sort()  # Process in sorted order
        self.logger.info(f"Found {len(input_files)} supported files to process")
        
        # Expand PDFs into individual pages and prepare processing list
        image_files = []
        pdf_temp_files = []  # Track temporary files for cleanup
        
        for file_path in input_files:
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext in ['.pdf']:
                # Extract pages from PDF
                try:
                    temp_pages = self.extract_images_from_pdf(file_path)
                    pdf_temp_files.extend(temp_pages)
                    
                    # Add each page as a separate processing item with metadata
                    for i, temp_page in enumerate(temp_pages):
                        image_files.append({
                            'path': temp_page,
                            'original_file': file_path,
                            'is_pdf_page': True,
                            'page_number': i + 1,
                            'display_name': f"{os.path.basename(file_path)} (Page {i + 1})"
                        })
                        
                except Exception as e:
                    self.logger.error(f"Error processing PDF {file_path}: {e}")
                    # Continue with other files
                    continue
            else:
                # Regular image file
                image_files.append({
                    'path': file_path,
                    'original_file': file_path,
                    'is_pdf_page': False,
                    'page_number': 1,
                    'display_name': os.path.basename(file_path)
                })
        
        if not image_files:
            self.logger.warning("No processable images found after expanding PDFs")
            return {"status": "error", "message": "No processable images found"}
        
        self.logger.info(f"Total images to process: {len(image_files)} (including PDF pages)")
        
        if self.max_workers == 1:
            self.logger.info("Processing files sequentially...")
        else:
            self.logger.info(f"Processing files with {self.max_workers} concurrent threads...")
        
        results = []
        pdf_paths = []
        
        try:
            if self.max_workers == 1:
                # Sequential processing (original behavior)
                for i, image_info in enumerate(image_files, 1):
                    result = self._process_single_file(image_info, i, len(image_files))
                    results.append(result)
                    if result["pdf_path"]:
                        pdf_paths.append(result["pdf_path"])
            else:
                # Concurrent processing
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    # Submit all tasks
                    future_to_info = {}
                    for i, image_info in enumerate(image_files, 1):
                        future = executor.submit(self._process_single_file, image_info, i, len(image_files))
                        future_to_info[future] = (image_info, i)
                    
                    # Collect results as they complete
                    completed_results = []
                    for future in as_completed(future_to_info):
                        result = future.result()
                        completed_results.append(result)
                    
                    # Sort results by page number to maintain order
                    completed_results.sort(key=lambda x: x["page_number"])
                    results = completed_results
                    
                    # Collect PDF paths
                    for result in results:
                        if result["pdf_path"]:
                            pdf_paths.append(result["pdf_path"])
        
        finally:
            # Clean up temporary PDF page files
            for temp_file in pdf_temp_files:
                try:
                    os.unlink(temp_file)
                    self.logger.debug(f"Cleaned up temporary file: {temp_file}")
                except OSError as e:
                    self.logger.warning(f"Could not clean up temporary file {temp_file}: {e}")
        
        # Count successful and failed processing
        successful = len([r for r in results if r["status"] == "success"])
        failed = len([r for r in results if r["status"] == "error"])
        
        self.logger.info(f"Processing completed: {successful} successful, {failed} failed")
        
        return {
            "status": "success",
            "pdf_paths": pdf_paths,
            "processed_files": len(image_files),
            "successful_files": successful,
            "failed_files": failed,
            "results": results
        }

    def create_searchable_pdf(self, results: List[Dict], output_filename: str) -> str:
        # Create output directory only when actually needed
        self.output_dir.mkdir(exist_ok=True)
        pdf_path = self.output_dir / output_filename
        
        # Create PDF document
        doc = SimpleDocTemplate(str(pdf_path), pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        temp_files = []  # Keep track of temp files to clean up later
        
        # Create custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
        )
        
        page_title_style = ParagraphStyle(
            'PageTitle',
            parent=styles['Heading2'],
            fontSize=12,
            spaceAfter=12,
        )
        
        transcription_style = ParagraphStyle(
            'Transcription',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=20,
            leftIndent=0,
            rightIndent=0,
        )
        
        # Add title page
        story.append(Paragraph("Handwritten Document Transcriptions", title_style))
        story.append(Spacer(1, 20))
        
        # Process each page
        for result in results:
            # Add page title
            story.append(Paragraph(f"Page {result['page_number']}: {result['filename']}", page_title_style))
            
            # Add image (resize if necessary)
            try:
                # Open and potentially resize image
                with Image.open(result['image_path']) as img:
                    # Calculate size to fit on page
                    img_width, img_height = img.size
                    max_width = 500  # points
                    max_height = 400  # points
                    
                    # Calculate scaling factor
                    width_ratio = max_width / img_width
                    height_ratio = max_height / img_height
                    scale_factor = min(width_ratio, height_ratio, 1.0)  # Don't upscale
                    
                    new_width = int(img_width * scale_factor)
                    new_height = int(img_height * scale_factor)
                    
                    # Create temporary resized image
                    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                        temp_path = temp_file.name
                        temp_files.append(temp_path)  # Track for cleanup later
                        resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        resized_img.save(temp_path, 'JPEG', quality=85)
                    
                    # Add image to PDF
                    story.append(ReportLabImage(temp_path, width=new_width, height=new_height))
                    story.append(Spacer(1, 12))
                    
            except Exception as e:
                print(f"Warning: Could not add image {result['filename']} to PDF: {e}")
                story.append(Paragraph(f"[Image: {result['filename']} - Could not display]", transcription_style))
            
            # Add transcription text (this makes the PDF searchable)
            # Clean the transcription text to prevent black squares in PDF
            cleaned_transcription = self.clean_text_for_pdf(result['transcription'])
            transcription_text = cleaned_transcription.replace('\n', '<br/>')
            story.append(Paragraph(f"<b>Transcription:</b><br/>{transcription_text}", transcription_style))
            story.append(Spacer(1, 30))
        
        # Build PDF
        try:
            doc.build(story)
            print(f"Successfully created searchable PDF: {pdf_path}")
            
            # Clean up temporary files after PDF is built
            for temp_path in temp_files:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass  # Ignore if file is already gone
            
            return str(pdf_path)
        except Exception as e:
            # Clean up temporary files even if PDF creation fails
            for temp_path in temp_files:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
            print(f"Error creating PDF: {e}")
            raise


def main():
    """Main function to run the OCR processing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Handwriting OCR using multiple AI providers (OpenAI, Claude, OpenRouter)")
    parser.add_argument("input_dir", help="Directory containing image files (JPEG, PNG) and PDF files")
    parser.add_argument("--api-key", help="API key for the chosen provider")
    parser.add_argument("--provider", choices=["openai", "anthropic", "openrouter", "google"], default="openai", 
                        help="AI provider to use (default: openai)")
    parser.add_argument("--output-dir", default="output", help="Output directory for results")
    parser.add_argument("--output-filename", default="transcribed_documents.pdf", help="Output PDF filename")
    parser.add_argument("--threads", "-t", type=int, default=1, help="Number of concurrent threads (default: 1)")
    
    args = parser.parse_args()
    
    # Validate threads argument
    if args.threads < 1:
        print("Error: Number of threads must be at least 1.")
        sys.exit(1)
    if args.threads > 10:
        print("Warning: Using more than 10 threads may hit API rate limits.")
    
    # Get API key based on provider
    api_key = args.api_key
    if not api_key:
        # Try to get from environment variables based on provider
        env_var_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
            "google": "GOOGLE_API_KEY"
        }
        env_var = env_var_map.get(args.provider)
        api_key = os.getenv(env_var)
        
        if not api_key:
            print(f"Error: API key is required for {args.provider}. Use --api-key or set {env_var} environment variable.")
            sys.exit(1)
    
    # Check input directory
    if not os.path.isdir(args.input_dir):
        print(f"Error: Input directory '{args.input_dir}' does not exist.")
        sys.exit(1)
    
    # Create OCR processor
    try:
        ocr = HandwritingOCR(api_key=api_key, provider=args.provider, output_dir=args.output_dir, max_workers=args.threads)
    except ImportError as e:
        print(f"Error: {e}")
        print(f"Please install the required library for {args.provider}:")
        if "anthropic" in str(e):
            print("  pip install anthropic")
        elif "requests" in str(e):
            print("  pip install requests")
        elif "openai" in str(e):
            print("  pip install openai")
        elif "google-generativeai" in str(e) or "Google GenerativeAI" in str(e):
            print("  pip install google-generativeai")
        sys.exit(1)
    except Exception as e:
        print(f"Error initializing {args.provider} provider: {e}")
        sys.exit(1)
    
    # Process batch
    try:
        results = ocr.process_batch(args.input_dir, args.output_filename)
        
        if results["status"] == "success":
            print(f"\n✅ Processing completed using {args.provider.upper()}!")
            print(f"📄 Created {len(results['pdf_paths'])} individual PDFs:")
            for pdf_path in results['pdf_paths']:
                print(f"   - {pdf_path}")
            print(f"📊 Processed {results['processed_files']} files")
            print(f"✅ Successful: {results['successful_files']}")
            if results['failed_files'] > 0:
                print(f"❌ Failed: {results['failed_files']}")
        else:
            print(f"\n❌ Processing failed: {results['message']}")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Error during processing: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

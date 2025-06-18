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
Handwriting transcription script using OpenAI API
Processes JPEG files, transcribes handwriting, and creates searchable PDFs.
"""

import os
import sys
import base64
import glob
from typing import List, Dict
import json
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import re
import unicodedata
import logging

import openai
from PIL import Image
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as ReportLabImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import tempfile


class HandwritingOCR:
    def __init__(self, api_key: str, output_dir: str = "output", max_workers: int = 1):
        """
        Initialize the HandwritingOCR processor.
        
        Args:
            api_key: OpenAI API key
            output_dir: Directory to save output files (only used for legacy combined PDF functionality)
            max_workers: Maximum number of concurrent threads for processing
        """
        self.client = openai.OpenAI(api_key=api_key)
        self.output_dir = Path(output_dir)
        # Don't create output_dir automatically - only create it when actually needed
        self.max_workers = max_workers
        self._lock = threading.Lock()  # For thread-safe operations
        
        # Set up logging
        self.logger = logging.getLogger('genea_htr')
        
        # Transcription configuration - centralized settings
        self.transcription_config = {
            "primary": {
                "model": "o4-mini",
                "reasoning_effort": "high",
                "max_completion_tokens": 8000,
                "prompt": """You are an expert in 18th-19th c. handwritten-document transcription. Transcribe exactly as shown—every character, punctuation, capitalization, space, line/page break, header/footer, marginal note, insertion, correction and error; preserve all formatting; do not modernize, correct, infer or hallucinate; enclose illegible text in [unclear]; account for any orientation. Purpose: academic research and historical preservation.  
Begin with:
Transcription:
"""
            },
            "fallback": {
                "model": "gpt-4o",
                "max_tokens": 8000,
                "temperature": 0.1,
                "prompt": """You are an expert historical-document transcriptionist for academic research and preservation. Transcribe all visible printed and handwritten text in document images exactly as shown—every character, punctuation, capitalization, space, line/paragraph break, header, title, date, signature, marginal note, annotation, insertion and error; preserve all formatting; do not modernize, infer or hallucinate; enclose illegible text in [unclear]; account for any orientation.  
Begin with:
Transcription:
"""
            }
        }
        
        # Refusal patterns to detect when AI refuses to transcribe
        self.refusal_patterns = [
            "I can't assist with that",
            "I'm sorry, I can't",
            "I'm unable to transcribe text from images",
            "unable to transcribe text from images",
            "consider using OCR",
            "Optical Character Recognition"
        ]

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

    def encode_image(self, image_path: str) -> str:
        """Encode image to base64 string for OpenAI API."""
        try:
            # First, check if the image needs conversion
            with Image.open(image_path) as img:
                # If image is not RGB, convert it
                if img.mode != 'RGB':
                    self.logger.info(f"Converting {os.path.basename(image_path)} from {img.mode} to RGB...")
                    rgb_img = img.convert('RGB')
                    
                    # Save to bytes buffer
                    import io
                    buffer = io.BytesIO()
                    rgb_img.save(buffer, format='JPEG', quality=95)
                    image_data = buffer.getvalue()
                    
                    return base64.b64encode(image_data).decode('utf-8')
                else:
                    # Image is already RGB, use original file
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
        
        # Prepare the base parameters
        api_params = {
            "model": config["model"],
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": config["prompt"]
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
        }
        
        # Add all other parameters from config (excluding model and prompt)
        for key, value in config.items():
            if key not in ["model", "prompt"]:
                api_params[key] = value
        
        response = self.client.chat.completions.create(**api_params)
        
        return response.choices[0].message.content

    def transcribe_image(self, image_path: str, max_retries: int = 3) -> str:
        """
        Transcribe handwriting from an image using OpenAI GPT-4O.
        
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
                footer_text = f"Generated by {self.transcription_config['primary']['model']} on {current_date}"
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

    def _process_single_file(self, image_path: str, page_number: int, total_files: int) -> Dict:
        """
        Process a single image file (for use in concurrent processing).
        
        Args:
            image_path: Path to the image file
            page_number: Page number for this file
            total_files: Total number of files being processed
            
        Returns:
            Dictionary with processing result for this file
        """
        filename = os.path.basename(image_path)
        
        # Thread-safe logging
        self.logger.info(f"Processing file {page_number}/{total_files}: {filename}")
        
        try:
            transcription = self.transcribe_image(image_path)
            
            # Create individual PDF for this image
            pdf_filename = f"{Path(image_path).stem}.pdf"
            pdf_path = self.create_individual_pdf(image_path, transcription, pdf_filename)
            
            self.logger.info(f"Completed file {page_number}/{total_files}: {filename}")
            
            return {
                "image_path": image_path,
                "filename": filename,
                "transcription": transcription,
                "pdf_path": pdf_path,
                "page_number": page_number,
                "status": "success"
            }
            
        except Exception as e:
            self.logger.error(f"Error processing file {page_number}/{total_files}: {filename} - {str(e)}")
            
            return {
                "image_path": image_path,
                "filename": filename,
                "transcription": f"[Error: {str(e)}]",
                "pdf_path": None,
                "page_number": page_number,
                "status": "error",
                "error": str(e)
            }

    def process_batch(self, input_dir: str, output_filename: str = "transcribed_documents.pdf") -> Dict:
        """
        Process a batch of JPEG files and create individual searchable PDFs.
        
        Args:
            input_dir: Directory containing JPEG files
            output_filename: Base name for output files (not used for individual PDFs)
            
        Returns:
            Dictionary with processing results
        """
        # Find all JPEG files
        jpeg_patterns = ["*.jpg", "*.jpeg", "*.JPG", "*.JPEG"]
        image_files = []
        
        for pattern in jpeg_patterns:
            image_files.extend(glob.glob(os.path.join(input_dir, pattern)))
        
        if not image_files:
            self.logger.warning(f"No JPEG files found in {input_dir}")
            return {"status": "error", "message": "No JPEG files found"}
        
        image_files.sort()  # Process in sorted order
        self.logger.info(f"Found {len(image_files)} JPEG files to process")
        
        if self.max_workers == 1:
            self.logger.info("Processing files sequentially...")
        else:
            self.logger.info(f"Processing files with {self.max_workers} concurrent threads...")
        
        results = []
        pdf_paths = []
        
        if self.max_workers == 1:
            # Sequential processing (original behavior)
            for i, image_path in enumerate(image_files, 1):
                result = self._process_single_file(image_path, i, len(image_files))
                results.append(result)
                if result["pdf_path"]:
                    pdf_paths.append(result["pdf_path"])
        else:
            # Concurrent processing
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                future_to_info = {}
                for i, image_path in enumerate(image_files, 1):
                    future = executor.submit(self._process_single_file, image_path, i, len(image_files))
                    future_to_info[future] = (image_path, i)
                
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
    
    parser = argparse.ArgumentParser(description="Handwriting OCR using OpenAI GPT-4O")
    parser.add_argument("input_dir", help="Directory containing JPEG files")
    parser.add_argument("--api-key", help="OpenAI API key (or set OPENAI_API_KEY environment variable)")
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
    
    # Get API key
    api_key = args.api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OpenAI API key is required. Use --api-key or set OPENAI_API_KEY environment variable.")
        sys.exit(1)
    
    # Check input directory
    if not os.path.isdir(args.input_dir):
        print(f"Error: Input directory '{args.input_dir}' does not exist.")
        sys.exit(1)
    
    # Create OCR processor
    ocr = HandwritingOCR(api_key=api_key, output_dir=args.output_dir, max_workers=args.threads)
    
    # Process batch
    try:
        results = ocr.process_batch(args.input_dir, args.output_filename)
        
        if results["status"] == "success":
            print(f"\n✅ Processing completed!")
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

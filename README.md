# Genealogy Assistant AI Handwritten Text Recognition Tool

A free cross-platform application designed to transcribe collections of historical documents into an easier-to-read format. It serves as a front-end to multiple AI APIs (OpenAI, Claude, OpenRouter, and Google Gemini), allowing you to convert image files (JPEG, PNG) and PDF documents into either searchable PDF files (with source images attached), plain text (txt) files, or CSV files.

This tool can transcribe thousands of images and PDF pages in a single batch, without the need for user intervention. It is generally not meant to provide 100% accurate transcriptions, as AI transcription are still not perfect, but it is designed to make large collections of documents more readable for humans. 

From within the application you can modify the prompt, model and parameters, enabling you to fine-tune how your images are processed. You can also enable multi-threading to have the application work on more than one image at a time.

## License

This software is licensed under the **GNU General Public License v3.0 (GPLv3)**. This means you are free to use, modify, and distribute this software under the terms of the GPL. See the [LICENSE](LICENSE) file for the full license text.

- **Freedom to use**: You can use this software for any purpose
- **Freedom to study and modify**: You have access to the source code and can modify it
- **Freedom to distribute**: You can share this software with others
- **Copyleft protection**: If you distribute modified versions, they must also be under GPLv3 

## Key Features

- **Simple Drag and Drop Interface**: No need for complicated command-line tools, simply drag and drop your image files (JPEG, PNG) and PDF documents directly into the application window to add them to the queue. 

- **Multiple File Format Support**: Process JPEG images, PNG images, and multi-page PDF documents. PDF files are automatically split into individual pages for processing.

- **Efficient Batch Processing**: This tool can transcribe multiple documents simultaneously, so you can speed up the process of working on large batches of images and PDFs. 

- **Multiple AI Providers**: Choose from OpenAI, Anthropic's Claude, Google Gemini, or any OpenRouter model with automatic fallback to secondary models if the primary model refuses or fails.

- **Highly Customizable Settings**: Fine-tune the AI's transcription behaviour to match your specific transcription needs with adjustable prompts and parameters such as temperature and token limits.

- **Flexible Output Formats**: Choose between searchable PDFs (that preserve the original image with embedded transcriptions), plain text or CSV files for lightweight, easily readable transcriptions. 

## AI Provider Support

This tool supports multiple AI providers, each with their own strengths and model options:

### OpenAI
- **Primary Model**: `o4-mini` with high reasoning effort for complex handwriting
- **Fallback Model**: `gpt-4o` with optimized settings
- **Requirements**: OpenAI API key and `openai` Python package

### Claude (Anthropic)  
- **Primary Model**: `claude-3-5-sonnet-20240620` for superior text recognition
- **Fallback Model**: `claude-3-haiku-20240307` for faster processing
- **Requirements**: Anthropic API key and `anthropic` Python package

### Google Gemini
- **Primary Model**: `gemini-1.5-pro` for advanced reasoning and complex handwriting
- **Fallback Model**: `gemini-1.5-flash` for faster and more cost-effective processing
- **Requirements**: Google API key and `google-generativeai` Python package

### OpenRouter
- **Primary Model**: `anthropic/claude-3.5-sonnet` via OpenRouter
- **Fallback Model**: `openai/gpt-4o` via OpenRouter  
- **Requirements**: OpenRouter API key and `requests` Python package
- **Benefits**: Access to multiple models through a single API

## Installation

### Prerequisites
- Python 3.7 or higher
- API key for your chosen provider:
  - **OpenAI**: Get from [OpenAI's website](https://platform.openai.com/api-keys)
  - **Anthropic**: Get from [Anthropic Console](https://console.anthropic.com/)
  - **OpenRouter**: Get from [OpenRouter](https://openrouter.ai/keys)
  - **Google Gemini**: Get from [Google AI Studio](https://makersuite.google.com/app/apikey)

### Dependencies

**Core dependencies (required for all providers):**
- `openai>=1.20.0`
- `Pillow>=10.0.0`
- `reportlab>=4.0.0`
- `tkinterdnd2-universal>=0.4.1` (GUI version only)
- `requests>=2.25.0`
- `PyMuPDF>=1.23.0` (for PDF processing support)

**Provider-specific dependencies:**
- **For Anthropic**: `anthropic>=0.25.0`
- **For Google Gemini**: `google-generativeai>=0.3.0`
- **For OpenRouter**: (uses `requests`, already included above)

### Quick Setup

1. **Install dependencies** by running the following command in your terminal:
   ```bash
   # For all providers
   pip install -r requirements.txt
   
   # Or install only what you need:
   # For OpenAI only:
   pip install openai Pillow reportlab tkinterdnd2-universal requests PyMuPDF
   
   # For Claude:
   pip install anthropic openai Pillow reportlab tkinterdnd2-universal requests PyMuPDF
   
   # For Google Gemini:
   pip install google-generativeai openai Pillow reportlab tkinterdnd2-universal requests PyMuPDF
   
   # For OpenRouter:
   pip install openai Pillow reportlab tkinterdnd2-universal requests PyMuPDF
   ```

2. **Configure your API key(s)**. The recommended way is to set them as environment variables:
   ```bash
   # For OpenAI
   export OPENAI_API_KEY="your-openai-key-here"
   
   # For Claude
   export ANTHROPIC_API_KEY="your-anthropic-key-here"
   
   # For Google Gemini
   export GOOGLE_API_KEY="your-google-api-key-here"
   
   # For OpenRouter  
   export OPENROUTER_API_KEY="your-openrouter-key-here"
   ```
   
   Alternatively, you can pass the key directly using the `--api-key` argument when you run the tool.

## Graphical User Interface (GUI)

For users who prefer a graphical interface, this tool also includes a GUI version.

### Starting the GUI

To launch the GUI, run the following command from your terminal:

```bash
python genea_htr_gui.py
```

This will open the GUI application that allows you to select your image directory, choose your AI provider, select your output format (PDF, TXT, or CSV), configure your API key, and start the transcription process without using command-line arguments.

## Quick Start

### Basic Usage
To process all supported files (JPEG, PNG, PDF) in a specific folder, provide the path to the directory.

```bash
# Process all supported files using default OpenRouter provider
python genea_htr.py /path/to/my-documents

# Use Claude instead of the default OpenRouter
python genea_htr.py /path/to/my-documents --provider anthropic

# Use Google Gemini
python genea_htr.py /path/to/my-documents --provider google

# Use OpenRouter
python genea_htr.py /path/to/my-documents --provider openrouter
```

### Advanced Usage
You can customize the tool's behavior with command-line arguments.

```bash
# Process files faster using multiple threads
python genea_htr.py /path/to/images --threads 2

# Use a specific provider and API key
python genea_htr.py /path/to/images --provider anthropic --api-key "your-anthropic-key"

# Save the output PDFs to a custom directory
python genea_htr.py /path/to/images --output-dir "results"

# Generate text files instead of PDFs
python genea_htr.py /path/to/images --output-format txt

# Generate a CSV file with all transcriptions
python genea_htr.py /path/to/images --output-format csv

# Combine options for maximum customization
python genea_htr.py /path/to/images --provider openrouter --threads 3 --api-key "your-key" --output-format csv
```

## File Organization

### Input Requirements
The tool supports multiple document formats:
- **JPEG images** (`.jpg`, `.jpeg`) - Direct image processing
- **PNG images** (`.png`) - Converted to JPEG for optimal API compatibility  
- **PDF documents** (`.pdf`) - Automatically split into individual pages for processing

The tool will automatically find all supported files in the directory you specify.

### Output Structure
By default, the tool creates output files in your input directory. For PDF and TXT formats, it creates a subdirectory (`PDF` or `TXT`). For CSV format, it creates a single file called `transcribed_images.csv` in the input directory.

**PDF Output Format (default):**
```
your-documents/
├── document1.jpg          # Your original JPEG image
├── document2.png          # Your original PNG image  
├── document3.pdf          # Your original PDF (3 pages)
└── PDF/                  # New folder created by the tool
    ├── document1.pdf      # Searchable PDF with image and transcription
    ├── document2.pdf      # Searchable PDF with image and transcription
    ├── document3_page_1.pdf  # Searchable PDF for PDF page 1
    ├── document3_page_2.pdf  # Searchable PDF for PDF page 2
    └── document3_page_3.pdf  # Searchable PDF for PDF page 3
```

**TXT Output Format:**
```
your-documents/
├── document1.jpg          # Your original JPEG image
├── document2.png          # Your original PNG image  
├── document3.pdf          # Your original PDF (3 pages)
└── TXT/                   # New folder created by the tool
    ├── document1.txt      # Plain text transcription with metadata header
    ├── document2.txt      # Plain text transcription with metadata header
    ├── document3_page_1.txt  # Plain text transcription for PDF page 1
    ├── document3_page_2.txt  # Plain text transcription for PDF page 2
    └── document3_page_3.txt  # Plain text transcription for PDF page 3
```

**CSV Output Format:**
```
your-documents/
├── document1.jpg          # Your original JPEG image
├── document2.png          # Your original PNG image  
├── document3.pdf          # Your original PDF (3 pages)
└── transcribed_images.csv # Single CSV file with all transcriptions
```

You can specify a different output location using the `--output-dir` option.

### Output File Structure

**PDF Files:**
Each generated PDF file contains:
- **Page 1+**: The complete text transcription with corresponding formatting.
- **Last page**: The original image, preserved at full resolution (equivalent to 300 DPI).

**TXT Files:**
Each generated TXT file contains:
- **Header**: Metadata including filename, AI provider, model used, and generation timestamp.
- **Body**: Clean text transcription optimized for readability and searchability.

**CSV Files:**
The generated CSV file contains:
- **Column 1 (filename)**: Name of the original image file
- **Column 2 (transcription)**: Full text transcription in plain text format
- **Column 3 (model)**: AI provider and model used for transcription
- **Column 4 (date)**: Generation timestamp

*Note: CSV text is automatically cleaned to handle Unicode characters and special symbols (like ≈, ø, æ) by converting them to ASCII equivalents for better compatibility with spreadsheet applications.*

## Command-Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `input_dir` | The directory containing image files (JPEG, PNG) and PDF documents to process. **Required**. | `python genea_htr.py ./documents` |
| `--provider` | AI provider to use: `openai`, `anthropic`, `google`, or `openrouter` (default: `openrouter`). | `--provider google` |
| `--api-key` | API key for the chosen provider. Optional if environment variable is set. | `--api-key "your-key"` |
| `--output-format` | Output format: `pdf`, `txt`, or `csv` (default: `pdf`). | `--output-format csv` |
| `--threads` or `-t` | Number of concurrent threads for processing (1-10, default: 1). | `--threads 3` |
| `--output-dir` | A custom directory for output files. Defaults to a `PDF` or `TXT` folder inside the `input_dir`. | `--output-dir "results"` |

## Concurrent Processing

The tool can process multiple files simultaneously to reduce the total processing time.

### Thread Count Recommendations
- **1 thread**: Processes files one by one. This is the slowest but most stable option.
- **2-3 threads**: A good balance of speed and stability, recommended for most use cases.
- **4+ threads**: Offers the fastest processing but increases the risk of hitting API rate limits.

### Examples
```bash
# For small batches (1-10 images), a single thread is sufficient
python genea_htr.py images/ --threads 1

# For medium batches (10-50 images), 2 threads are recommended
python genea_htr.py images/ --threads 2

# For large batches (50+ images), consider using 3 or more threads
python genea_htr.py images/ --threads 3
```

## How It Works

1. **File Discovery**: The tool scans the specified directory and finds all supported files (JPEG, PNG, PDF).
2. **File Processing**: 
   - **JPEG/PNG images**: Processed directly (PNG files are converted to JPEG for API compatibility)
   - **PDF documents**: Automatically split into individual pages at 300 DPI resolution for processing
3. **AI Transcription**: Each image is sent to your chosen AI provider's primary model for transcription. If this fails, it automatically retries with a fallback model from the same provider.
4. **Specialized Prompts**: It uses carefully designed prompts optimized for transcribing handwritten text from historical documents.
5. **Output Generation**: Based on your chosen format, either a searchable PDF (containing the full-resolution image and transcribed text) or a plain text file (with metadata header and transcription) is generated for each image. For CSV output, a single file is created for all images in the batch.
6. **Text Cleaning**: The transcribed text is sanitized to remove problematic characters and ensure optimal output quality.

## Example Workflow

1. **Prepare your documents** in a single folder:
   ```
   my-documents/
   ├── handwritten_letter.jpg    # JPEG image
   ├── old_document.png          # PNG image  
   └── multi_page_record.pdf     # PDF document (3 pages)
   ```

2. **Run the tool**, specifying the folder, output format, and desired number of threads:
   ```bash
   # For PDF output (default)
   python genea_htr.py my-documents/ --threads 2
   
   # For TXT output
   python genea_htr.py my-documents/ --output-format txt --threads 2
   
   # For CSV output
   python genea_htr.py my-documents/ --output-format csv --threads 2
   ```

3. **Find your results** in the newly created folder:

   **PDF Output:**
   ```
   my-documents/
   ├── handwritten_letter.jpg
   ├── old_document.png
   ├── multi_page_record.pdf
   └── PDF/
       ├── handwritten_letter.pdf          # Searchable PDF from JPEG
       ├── old_document.pdf                # Searchable PDF from PNG
       ├── multi_page_record_page_1.pdf    # Searchable PDF from PDF page 1
       ├── multi_page_record_page_2.pdf    # Searchable PDF from PDF page 2
       └── multi_page_record_page_3.pdf    # Searchable PDF from PDF page 3
   ```

   **TXT Output:**
   ```
   my-documents/
   ├── handwritten_letter.jpg
   ├── old_document.png
   ├── multi_page_record.pdf
   └── TXT/
       ├── handwritten_letter.txt          # Text transcription from JPEG
       ├── old_document.txt                # Text transcription from PNG
       ├── multi_page_record_page_1.txt    # Text transcription from PDF page 1
       ├── multi_page_record_page_2.txt    # Text transcription from PDF page 2
       └── multi_page_record_page_3.txt    # Text transcription from PDF page 3
   ```

   **CSV Output:**
   ```
   my-documents/
   ├── handwritten_letter.jpg
   ├── old_document.png
   ├── multi_page_record.pdf
   └── transcribed_images.csv             # Single CSV with all transcriptions
   ```

## Cost Considerations

- This tool uses paid AI API services. The cost depends on the provider, model used, and complexity of the images. 
- All providers use a maximum of 8000 tokens per image by default.
- Process a small batch of images first to estimate the cost.
- Regularly check your API usage on your provider's dashboard:
  - OpenAI: [Usage Dashboard](https://platform.openai.com/usage)
  - Claude: [Anthropic Console](https://console.anthropic.com/)
  - Google Gemini: [Google AI Studio](https://makersuite.google.com/)
  - OpenRouter: [Usage Page](https://openrouter.ai/activity)

## Troubleshooting

### Common Issues

- **Error: "API key is required"**: Ensure you have set the appropriate environment variable (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, or `OPENROUTER_API_KEY`) or are using the `--api-key` option.
- **Error: "Unsupported provider"**: Make sure you're using one of the supported providers: `openai`, `anthropic`, `google`, or `openrouter`.
- **Import errors**: Install the required library for your chosen provider (see installation instructions above).
- **Error: "No supported files found"**: Verify that the directory path is correct and that it contains files with `.jpg`, `.jpeg`, `.png`, or `.pdf` extensions.
- **Error: "PyMuPDF is required for PDF processing"**: Install PyMuPDF with `pip install PyMuPDF` to process PDF files.
- **Symptom: Processing is slow**: This can be caused by a slow internet connection or high load on the AI provider's API. Try reducing the number of threads.
- **Symptom: Empty transcriptions**: The tool automatically uses a fallback model to prevent this. Check that your images are clear, readable, and contain text.
- **Symptom: Large PDF files take a long time**: Multi-page PDFs are processed page by page. Consider splitting large PDFs into smaller files or using more threads.

### Getting Help
If you encounter problems, follow these steps:
- Review the console output for specific error messages.
- Ensure your API key is correct and your account has sufficient credits.
- Try processing a single file to isolate the problem.
- Consider switching to a different provider if one is experiencing issues.

## Best Practices

### Performance Tips
- Use high-resolution images for the most accurate transcriptions.
- Start with small batches to fine-tune your settings.
- Use 1-2 threads for a balance of speed and reliability.
- Monitor your API usage during large processing jobs.
- Ensure you have a stable internet connection for best performance.
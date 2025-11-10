# Genealogy Assistant AI Handwritten Text Recognition Tool

A free cross-platform application designed to transcribe collections of historical documents into an easier-to-read format. It serves as a front-end to multiple AI APIs (OpenAI, Claude, OpenRouter, and Google Gemini), allowing you to convert image files (JPEG, PNG) and PDF documents into searchable PDF files, plain text files, or CSV files.

This tool can transcribe thousands of images and PDF pages in a single batch, without the need for user intervention. It is generally not meant to provide 100% accurate transcriptions, as AI transcriptions are still not perfect, but it is designed to make large collections of documents more readable for humans.

From within the application you can modify the prompt, model and parameters, enabling you to fine-tune how your images are processed. You can also enable multi-threading to have the application work on more than one image at a time.

## License

Licensed under **GNU General Public License v3.0 (GPLv3)**. You are free to use, modify, and distribute this software. See the [LICENSE](LICENSE) file for details.

## Key Features

- **Simple Drag and Drop Interface**: No need for complicated command-line tools, simply drag and drop your image files (JPEG, PNG) and PDF documents directly into the application window to add them to the queue.

- **Multiple File Format Support**: Process JPEG images, PNG images, and multi-page PDF documents. PDF files are automatically split into individual pages for processing.

- **Efficient Batch Processing**: This tool can transcribe multiple documents simultaneously, so you can speed up the process of working on large batches of images and PDFs.

- **Multiple AI Providers**: Choose from OpenAI, Anthropic's Claude, Google Gemini, or any OpenRouter model with automatic fallback to secondary models if the primary model refuses or fails.

- **Highly Customizable Settings**: Fine-tune the AI's transcription behaviour to match your specific transcription needs with adjustable prompts and parameters such as temperature and token limits.

- **Flexible Output Formats**: Choose between individual PDFs with images, individual text-only PDFs, merged PDFs (single file with all transcriptions, with or without images), plain text files, or CSV files for lightweight, easily readable transcriptions.

## AI Provider Support

| Provider | Primary Model | Fallback Model | Requirements |
|----------|---------------|----------------|--------------|
| **OpenRouter** | qwen/qwen3-vl-235b-a22b-instruct | openai/gpt-5-mini | OpenRouter API key, `requests` package |
| **Google Gemini** | gemini-2.5-flash-preview-09-2025 | gemini-2.5-flash-lite-preview-09-2025 | Google API key, `google-generativeai` package |
| **OpenAI** | gpt-5-mini | gpt-4o-mini | OpenAI API key, `openai` package |
| **Claude** | claude-sonnet-4-5 | claude-haiku-4-5 | Anthropic API key, `anthropic` package |

## Pricing Information

All providers charge based on token usage (input tokens for images sent, output tokens for transcriptions received). Costs can vary significantly between providers.

### Token Costs by Provider

| Provider | Model Type | Model Name | Input Cost | Output Cost |
|----------|-----------|------------|------------|-------------|
| **OpenRouter** | Primary | qwen/qwen3-vl-235b-a22b-instruct | $0.22/M tokens | $0.88/M tokens |
| | Fallback | openai/gpt-5-mini | $0.25/M tokens | $2.00/M tokens |
| **Google Gemini** | Primary | gemini-2.5-flash-preview-09-2025 | $0.30/M tokens | $2.50/M tokens |
| | Fallback | gemini-2.5-flash-lite-preview-09-2025 | $0.10/M tokens | $0.40/M tokens |
| **OpenAI** | Primary | gpt-5-mini | $0.25/M tokens | $2.00/M tokens |
| | Fallback | gpt-4o-mini | $0.15/M tokens | $0.60/M tokens |
| **Claude** | Primary | claude-sonnet-4-5 | $3.00/M tokens | $15.00/M tokens |
| | Fallback | claude-haiku-4-5 | $1.00/M tokens | $5.00/M tokens |

## Installation

### Prerequisites
- Python 3.7 or higher
- API key for your chosen provider:
  - **OpenRouter**: Get from [OpenRouter](https://openrouter.ai/keys)
  - **Google Gemini**: Get from [Google AI Studio](https://makersuite.google.com/app/apikey)
  - **OpenAI**: Get from [OpenAI's website](https://platform.openai.com/api-keys)
  - **Anthropic**: Get from [Anthropic Console](https://console.anthropic.com/)

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

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set API key** (choose one method):
   ```bash
   # Environment variable (recommended)
   export OPENROUTER_API_KEY="your-key-here"
   export GOOGLE_API_KEY="your-key-here"
   export OPENAI_API_KEY="your-key-here"
   export ANTHROPIC_API_KEY="your-key-here"
   
   # Or use --api-key argument when running
   ```

## Usage

## Graphical User Interface (GUI)

For users who prefer a graphical interface, this tool also includes a GUI version.

### Starting the GUI

To launch the GUI, run the following command from your terminal:

```bash
python genea_htr_gui.py
```

This will open the GUI application that allows you to drag and drop your image files and PDFs, choose your AI provider, select your output format, configure the number of concurrent threads, and start the transcription process without using command-line arguments.

### GUI Features

- **Drag & Drop Interface**: Simply drag image files (JPEG, PNG) and PDF documents directly into the application window
- **Provider Selection**: Choose from OpenRouter, Google, OpenAI, or Anthropic
- **Output Format Options**: 
  - **PDF with images**: Individual searchable PDFs with source images (default)
  - **PDF with images (merged)**: Single merged PDF with all transcriptions and source images
  - **PDF**: Individual text-only searchable PDFs
  - **PDF (merged)**: Single merged text-only PDF
  - **TXT**: Individual text files
  - **CSV**: Single CSV file with all transcriptions
- **Threads Control**: Adjust concurrent processing threads (1-5) directly from the main screen
- **API Settings**: Configure API keys and advanced model settings through the API Settings dialog
- **Output Location**: Choose to save files in source folder or custom location
- **Real-time Progress**: Live progress tracking with optional log viewer during processing

## Quick Start

### Basic Usage
To process all supported files (JPEG, PNG, PDF) in a specific folder, provide the path to the directory.

```bash
# Process all files in directory (default: OpenRouter, PDF with images)
python genea_htr.py /path/to/documents

# Use different providers
python genea_htr.py /path/to/documents --provider google
python genea_htr.py /path/to/documents --provider openai
python genea_htr.py /path/to/documents --provider anthropic
```

**Advanced options:**
```bash
# Multiple threads and custom output
python genea_htr.py /path/to/images --threads 3 --output-format txt --output-dir results

# Different output formats
python genea_htr.py /path/to/images --output-format csv
python genea_htr.py /path/to/images --output-format merged-pdf
python genea_htr.py /path/to/images --output-format pdf --no-images  # text-only PDFs
```

### Command-Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `input_dir` | Directory containing files to process (**required**) | `./documents` |
| `--provider` | AI provider: `openrouter` (default), `google`, `openai`, `anthropic` | `--provider google` |
| `--api-key` | API key (optional if env variable set) | `--api-key "your-key"` |
| `--output-format` | `pdf` (default), `txt`, `csv`, `merged-pdf` | `--output-format txt` |
| `--no-images` | Create text-only PDFs | `--no-images` |
| `--threads` | Concurrent threads (1-10, default: 1) | `--threads 3` |
| `--output-dir` | Custom output directory | `--output-dir "results"` |

## File Organization

### Input Support
- **JPEG/PNG images** - Processed directly (PNG converted to JPEG for API compatibility)
- **PDF documents** - Automatically split into individual pages at 300 DPI

### Output Structure
```
your-documents/
├── document1.jpg                    # Original files
├── document2.png                    
├── document3.pdf                    # Multi-page PDF
├── PDF/                             # Individual PDFs (default)
│   ├── document1.pdf               # Searchable PDF with image + text
│   ├── document2.pdf               
│   ├── document3_page_1.pdf        # PDF pages processed separately
│   └── document3_page_2.pdf        
├── TXT/                            # Text format output
│   ├── document1.txt               # Plain text with metadata
│   └── document2.txt               
├── transcribed_images.csv          # CSV format (single file)
└── transcribed_images.pdf       # Merged PDF format (single file)
```

**Output formats:**
- **Individual PDFs** (default): Searchable PDFs with transcription + optional source image
- **Merged PDF**: Single PDF with all transcriptions + optional source images
- **TXT files**: Plain text with metadata headers
- **CSV file**: Filename, transcription, model, date columns

## How It Works

1. **File Discovery**: The tool scans the specified directory and finds all supported files (JPEG, PNG, PDF).
2. **File Processing**: 
   - **JPEG/PNG images**: Processed directly (PNG files are converted to JPEG for API compatibility)
   - **PDF documents**: Automatically split into individual pages at 300 DPI resolution for processing
3. **AI Transcription**: Each image is sent to your chosen AI provider's primary model for transcription. If this fails, it automatically retries with a fallback model from the same provider.
4. **Specialized Prompts**: It uses carefully designed prompts optimized for transcribing handwritten text from historical documents.
5. **Output Generation**: Based on your chosen format, the tool generates the appropriate output files.
6. **Text Cleaning**: The transcribed text is sanitized to remove problematic characters and ensure optimal output quality.

## Example Workflow

1. **Prepare documents** in a folder
2. **Run the tool:**
   ```bash
   python genea_htr.py my-documents/ --threads 2 --output-format pdf
   ```
3. **Find results** in the `PDF/` subdirectory or specified output location

## Threading & Performance

- **1 thread**: Slowest but most stable
- **2-3 threads**: Recommended balance of speed and stability  
- **4+ threads**: Fastest but may hit API rate limits

## Cost Considerations

- This tool uses paid AI API services. See the [Pricing Information](#pricing-information) section above for detailed cost breakdowns by provider.
- The cost depends on the provider, model used, image complexity, and document length.
- All providers use a maximum of 8,000 output tokens per image by default to control costs.
- **Important:** Always process a small test batch (5-10 images) first to estimate costs for your specific documents before processing large collections.
- Regularly check your API usage on your provider's dashboard:
  - OpenRouter: [Usage Page](https://openrouter.ai/activity)
  - Google Gemini: [Google AI Studio](https://makersuite.google.com/)
  - OpenAI: [Usage Dashboard](https://platform.openai.com/usage)
  - Claude: [Anthropic Console](https://console.anthropic.com/)

## Troubleshooting

**Common Issues:**
- **"API key is required"**: Set environment variable or use `--api-key`
- **"Unsupported provider"**: Use `openrouter`, `google`, `openai`, or `anthropic`
- **Import errors**: Install required provider package (see Installation)
- **"No supported files found"**: Check directory path and file extensions
- **"PyMuPDF is required"**: Install with `pip install PyMuPDF`
- **Slow processing**: Reduce threads or check internet connection
- **Empty transcriptions**: Ensure images are clear and readable

**Getting Help:**
- Check console output for error messages
- Verify API key and account credits
- Test with single file first
- Try different provider if issues persist

## Best Practices

- Use high-resolution images for best accuracy
- Start with small batches to test settings
- Use 1-2 threads for reliability
- Monitor API usage during large jobs
- Ensure stable internet connection
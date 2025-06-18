# Genealogy Assistant AI Handwritten Text Recognition Tool

A free cross-platform application designed to transcribe collections of historical documents into an easier-to-read format. It serves as a front-end to the OpenAI API, allowing you to convert image files into searchable, transcribed PDF's with the source image attached. 

This tool can transcribe thousands of images in a single batch, without the need for user intervention. It is generally not meant to provide 100% accurate transcriptions, as AI transcription are still not perfect, but it is designed to make large collections of documents more readable for humans. 

From within the application you can modify the prompt, model and parameters, enabling you to fine-tune how your images are processed. You can also enable multi-threading to have the application work on more than one image at a time.

## License

This software is licensed under the **GNU General Public License v3.0 (GPLv3)**. This means you are free to use, modify, and distribute this software under the terms of the GPL. See the [LICENSE](LICENSE) file for the full license text.

- **Freedom to use**: You can use this software for any purpose
- **Freedom to study and modify**: You have access to the source code and can modify it
- **Freedom to distribute**: You can share this software with others
- **Copyleft protection**: If you distribute modified versions, they must also be under GPLv3 

## Key Features

- **Simple Drag and Drop Interface**: No need for complicated command-line tools, simply drag and drop your image files directly into the application window to add them to the queue. 

- **Efficient Batch Processing**: This tool can transcribe multiple documents simultaneously, so you can speed up the process of working on large batches of images. 

- **Advanced AI Models**: You can use any of OpenAI's powerful models such as the default model of o4-mini-high, including the ability to fall back to a secondary model if the primary model refuses or fails.

- **Highly Customizable Settings**: Fine-tune the AI’s transcription behaviour to match your specific transcription needs with adjustable prompts and parameters such as temperature and token limits.

- **Instantly Searchable PDFs**: Your documents are converted into PDFs that preserve the original image while embedding high-quality, searchable transcriptions that are more easily readable. 

## Installation

### Prerequisites
- Python 3.7 or higher
- An active OpenAI API key

### Dependencies
- `openai>=1.20.0`
- `Pillow>=10.0.0`
- `reportlab>=4.0.0`
- `tkinterdnd2>=0.3.0` (GUI version only)

### Quick Setup
1. **Install dependencies** by running the following command in your terminal:
   ```bash
   pip install -r requirements.txt
   ```
2. **Configure your OpenAI API key**. You can get a key from [OpenAI's website](https://platform.openai.com/api-keys).
   Set it as an environment variable for the tool to use it automatically:
     ```bash
     export OPENAI_API_KEY="your-api-key-here"
     ```
   Alternatively, you can pass the key directly using the `--api-key` argument when you run the tool.

## Graphical User Interface (GUI)

For users who prefer a graphical interface, this tool also includes a GUI version.

### Starting the GUI

To launch the GUI, run the following command from your terminal:

```bash
python genea_htr_gui.py
```

This will open the GUI application that allows you to select your image directory, enter your API key, and start the transcription process without using command-line arguments.

## Quick Start

### Basic Usage
To process all JPEG files in a specific folder, provide the path to the directory.

```bash
# Process all JPEG files in a folder named "my-documents"
python genea_htr.py /path/to/my-documents
```

### Advanced Usage
You can customize the tool's behavior with command-line arguments.

```bash
# Process files faster using multiple threads
python genea_htr.py /path/to/images --threads 2

# Use a specific API key instead of an environment variable
python genea_htr.py /path/to/images --api-key "your-api-key"

# Save the output PDFs to a custom directory
python genea_htr.py /path/to/images --output-dir "results"
```

## File Organization

### Input Requirements
The tool is designed to work with images in JPEG format (`.jpg` or `.jpeg`). It will automatically find all JPEG files in the directory you specify.

### Output Structure
By default, the tool creates a `PDFs` subdirectory inside your input directory to store the generated files.

```
your-images/
├── document1.jpg          # Your original image
├── document2.jpg          # Your original image
└── PDFs/                  # New folder created by the tool
    ├── document1.pdf      # Searchable PDF with image and transcription
    └── document2.pdf      # Searchable PDF with image and transcription
```

You can specify a different output location using the `--output-dir` option.

### PDF Structure
Each generated PDF file contains:
- **Page 1+**: The complete text transcription with corresponding formatting.
- **Last page**: The original image, preserved at full resolution (equivalent to 300 DPI).

## Command-Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `input_dir` | The directory containing JPEG files to process. **Required**. | `python genea_htr.py ./images` |
| `--api-key` | Your OpenAI API key. Optional if the `OPENAI_API_KEY` environment variable is set. | `--api-key "sk-..."` |
| `--threads` or `-t` | Number of concurrent threads for processing (1-10, default: 1). | `--threads 3` |
| `--output-dir` | A custom directory for output PDFs. Defaults to a `PDFs` folder inside the `input_dir`. | `--output-dir "results"` |

## Concurrent Processing

The tool can process multiple files simultaneously to reduce the total processing time.

### Thread Count Recommendations
- **1 thread**: Processes files one by one. This is the slowest but most stable option.
- **2-3 threads**: A good balance of speed and stability, recommended for most use cases.
- **4+ threads**: Offers the fastest processing but increases the risk of hitting OpenAI API rate limits.

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

1. **Image Discovery**: The tool scans the specified directory and finds all JPEG files.
2. **AI Transcription**: Each image is sent to OpenAI's `o4-mini-high` model for transcription. If this fails, it automatically retries with the more powerful `GPT-4o` model.
3. **Specialized Prompts**: It uses carefully designed prompts optimized for transcribing handwritten text from historical documents.
4. **PDF Generation**: A searchable PDF is created for each image, containing the full-resolution image and the transcribed text.
5. **Text Cleaning**: The transcribed text is sanitized to remove characters that could cause issues when creating the PDF.

## Example Workflow

1. **Prepare your images** in a single folder:
   ```
   my-images/
   ├── image1.jpg
   ├── image2.jpg
   └── image3.jpg
   ```

2. **Run the tool**, specifying the folder and desired number of threads:
   ```bash
   python genea_htr.py my-images/ --threads 2
   ```

3. **Find your results** in the newly created `PDFs` folder:
   ```
   my-images/
   ├── image1.jpg
   ├── image2.jpg
   ├── image3.jpg
   └── PDFs/
       ├── image1.pdf          # New searchable PDF
       ├── image2.pdf       # New searchable PDF
       └── image3.pdf # New searchable PDF
   ```

## Cost Considerations

This tool uses OpenAI's paid API services. The cost depends on the model used and the complexity of the images.
- **Primary Model**: The primary model uses `o4-mini-high` by default, with a maximum of 8000 tokens per image.
- **Fallback Model**: The fallback model uses `GPT-4o` by default, with a maximum of 8000 tokens per image and a temperature of 0.1.

### Cost-Saving Tips
- Start with a small number of threads (1 or 2) to monitor your spending.
- Process a small batch of images first to estimate the cost.
- Regularly check your API usage on the [OpenAI dashboard](https://platform.openai.com/usage).

## Troubleshooting

### Common Issues

- **Error: "OpenAI API key is required"**: Ensure you have set the `OPENAI_API_KEY` environment variable or are using the `--api-key` option.
- **Error: "No JPEG files found"**: Verify that the directory path is correct and that it contains files with `.jpg` or `.jpeg` extensions.
- **Symptom: Processing is slow**: This can be caused by a slow internet connection or high load on the OpenAI API. Try reducing the number of threads.
- **Symptom: Empty transcriptions**: The tool automatically uses a fallback model to prevent this. Check that your images are clear, readable, and contain text.

### Getting Help
If you encounter problems, follow these steps:
- Review the console output for specific error messages.
- Ensure your OpenAI API key is correct and your account has sufficient credits.
- Try processing a single file to isolate the problem.

## Best Practices

### Performance Tips
- Use high-resolution images for the most accurate transcriptions.
- Start with small batches to fine-tune your settings.
- Use 1-2 threads for a balance of speed and reliability.
- Monitor your API usage during large processing jobs.
- Ensure you have a stable internet connection for best performance.
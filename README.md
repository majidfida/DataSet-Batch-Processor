# DataSet-Batch-Processor

I developed this multi-functional image and text batch processing tool with zero coding experience, leveraging ChatGPT to assist in implementing the tiled dataset approach. After achieving remarkable results on a small dataset, I was inspired by a Reddit discussion on the Flux Sigma Vision Alpha 1 model and decided to scale up to larger datasets. This led me to create a script that generates tiles and unified captions, streamlining the model training process. The impressive outcomes motivated me to share this tool with the community, incorporating additional features for batch prompt preparation and image conversion to facilitate dataset creation.

For more information on the Flux Sigma Vision Alpha 1 model and its tiled dataset approach, please refer to the Reddit discussion: https://www.reddit.com/r/StableDiffusion/comments/1iizgll/flux_sigma_vision_alpha_1_base_model/

**A multi-functional image and text batch processing tool built with Python and Gradio. This tool offers a suite of functionalities including:**

- **Image Tiling & Manual Captioning**: Tile images into smaller pieces with configurable overlap and optional captions.
- **Merge Text Files**: Combine multiple `.txt` files from a folder into a single output file.
- **Image Format Converter**: Convert images between formats (supports JPG, PNG, BMP, TIFF, GIF, WEBP, HEIC, and RAW formats like CR2, NEF, ARW, DNG) with dynamic UI options for quality/compression.
- **Split JSONL File**: Divide a JSONL file into multiple files based on the specified number of lines, ignoring lines with digits.
- **Remove Duplicates**: Remove duplicate lines from a text file.
- **Split Large Text File**: Split a large text file into smaller files based on a line count.

## Features

- **Dynamic UI Controls:**  
  - Dropdown menus to select input and output image formats.
  - A JPEG quality slider and PNG compression slider that appear dynamically when the respective format is chosen.
- **Extended Format Support:**  
  - Supports HEIC/HEIF images via [pillow-heif](https://github.com/metachris/pillow-heif).
  - Supports RAW formats (CR2, NEF, ARW, DNG) and improved GIF/WebP handling using [imageio](https://github.com/imageio/imageio) (if installed).
- **Gradio Web Interface:**  
  - The interface automatically opens in your default browser at [http://127.0.0.1:7860](http://127.0.0.1:7860).

## Dependencies

This project relies on several third-party libraries. Please review and install them as needed:

- [Python 3.x](https://www.python.org/)
- [Gradio](https://github.com/gradio-app/gradio) (MIT License)
- [Pillow](https://github.com/python-pillow/Pillow) (HPND License)
- [pillow-heif](https://github.com/metachris/pillow-heif) (MIT License) *(optional, for HEIC/HEIF support)*
- [imageio](https://github.com/imageio/imageio) (BSD License) *(optional, for RAW, GIF, WebP support)*
- [tqdm](https://github.com/tqdm/tqdm) (MPLv2 License)

## Installation

Use the one-click installer on Windows.

**Manual Installation**

1. **Clone the repository:**

   ```bash
   git clone https://github.com/majidfida/dataset-batch-processor.git
   cd dataset-batch-processor

    Create and activate a virtual environment (optional but recommended):

python -m venv venv

On Unix/macOS:

source venv/bin/activate

On Windows:

venv\Scripts\activate

Install the required dependencies:

    pip install -r requirements.txt

Usage

Run the script with:

python batch_processor.py

or use the provided start_app.bat.

Changelog
[New Update]

    Modular Architecture:
    The main app has been refactored into multiple modules instead of a single Python file. This change improves code organization and maintainability.

    Unified Captions for Tiled Images:
    A unified caption management system has been added. Users can now select from a list of pre-written captions (loaded from Unified_Caps.txt) or enter their own custom caption. Additionally, there's a "Save Caption" option that stores user-defined captions to be reused in future tiling tasks.

Disclaimer: Use at your own risk; always keep backups.

Credits: Eagle-42

import os
import shutil
import zipfile
import threading

import gradio as gr
from PIL import Image
from tqdm import tqdm

# Enable HEIC/HEIF support if pillow-heif is installed
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

# Try to import imageio for RAW and improved GIF/WebP handling
try:
    import imageio.v3 as iio
except ImportError:
    iio = None

stop_event = threading.Event()


def stop_process():
    """Signal any running process to stop."""
    stop_event.set()
    return "Stop request sent."


def check_output_empty(output_folder):
    """Return (True, "") if output_folder exists and is empty, else (False, error_message)."""
    if not os.path.isdir(output_folder):
        return False, f"Output folder does not exist: {output_folder}"
    if os.listdir(output_folder):
        return False, "Output folder is not empty. Please provide an empty folder."
    return True, ""


# --------------------------------------------------------------------------------
# TILING CODE (TAB 1)
# --------------------------------------------------------------------------------

def ensure_output_folder(path):
    os.makedirs(path, exist_ok=True)


def tile_image(image_path, tile_size, overlap_ratio, padding, num_tiles, caption_text, output_path, output_format):
    """
    Tiling a single image. Returns a list of tile file paths.
    Checks stop_event to allow stopping mid-process.
    """
    if stop_event.is_set():
        return []

    image = Image.open(image_path)
    image_width, image_height = image.size
    ensure_output_folder(output_path)

    # Dynamically compute tile size if num_tiles is given (assumes square grid)
    if num_tiles:
        tile_size = min(image_width, image_height) // int(num_tiles ** 0.5)

    step = tile_size - int(overlap_ratio * tile_size)
    horizontal_tiles = max(0, (image_width - padding) // step)
    vertical_tiles = max(0, (image_height - padding) // step)

    # Map output_format to PIL save format (default to PNG if "None")
    format_mapping = {"JPG": "JPEG", "PNG": "PNG", "NONE": "PNG"}
    save_format = format_mapping.get(output_format.upper(), "PNG")

    tile_paths = []
    for j in tqdm(range(vertical_tiles), desc=f"Tiling rows of {os.path.basename(image_path)}"):
        if stop_event.is_set():
            return tile_paths
        for i in range(horizontal_tiles):
            if stop_event.is_set():
                return tile_paths
            left = i * step
            upper = j * step
            right = min(left + tile_size, image_width)
            lower = min(upper + tile_size, image_height)
            tile = image.crop((left, upper, right, lower))
            base_name = os.path.splitext(os.path.basename(image_path))[0]
            file_extension = "jpg" if save_format == "JPEG" else "png"
            tile_filename = f"{base_name}_tile_{i}_{j}.{file_extension}"
            tile_path = os.path.join(output_path, tile_filename)
            tile.save(tile_path, format=save_format)
            tile_paths.append(tile_path)

            if caption_text:
                caption_filename = f"{base_name}_tile_{i}_{j}.txt"
                caption_path = os.path.join(output_path, caption_filename)
                with open(caption_path, "w", encoding="utf-8") as f:
                    f.write(caption_text)
    return tile_paths


def process_images_from_folder(folder_path, tile_size, overlap_ratio, padding, num_tiles, caption_text, output_path, output_format):
    """
    Tiling an entire folder of images. Returns (message, list_of_tile_paths).
    """
    valid, msg = check_output_empty(output_path)
    if not valid:
        return msg, []

    stop_event.clear()

    if not os.path.isdir(folder_path):
        return "Invalid input folder path.", []

    all_tile_paths = []
    try:
        for filename in os.listdir(folder_path):
            if stop_event.is_set():
                return "Process stopped by user.", all_tile_paths
            if filename.lower().endswith((".png", ".jpg", ".jpeg", ".heic", ".cr2", ".nef", ".arw", ".dng")):
                image_path = os.path.join(folder_path, filename)
                tile_paths = tile_image(image_path, tile_size, overlap_ratio, padding, num_tiles, caption_text, output_path, output_format)
                all_tile_paths.extend(tile_paths)
                if stop_event.is_set():
                    return "Process stopped by user.", all_tile_paths

        return f"Tiling complete! {len(all_tile_paths)} tiles created.", all_tile_paths
    except Exception as e:
        return f"Error: {str(e)}", []


def create_zip(output_path):
    """Zip up the contents of output_path into processed_tiles.zip."""
    zip_file = os.path.join(output_path, "processed_tiles.zip")
    try:
        with zipfile.ZipFile(zip_file, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(output_path):
                for file in files:
                    if file == "processed_tiles.zip":
                        continue
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, arcname=file)
        return zip_file
    except Exception as e:
        return f"Error creating ZIP: {str(e)}"


def on_tiling(folder_path, tile_size, overlap_ratio, padding, num_tiles, caption_text, output_path, output_format):
    """Gradio event handler for the Tiling tab."""
    message, tile_paths = process_images_from_folder(folder_path, tile_size, overlap_ratio, padding, num_tiles, caption_text, output_path, output_format)
    return message, tile_paths


# --------------------------------------------------------------------------------
# OTHER TASKS (Tabs 2, 4, 5, 6)
# --------------------------------------------------------------------------------

def merge_text_files(input_folder, output_folder):
    valid, msg = check_output_empty(output_folder)
    if not valid:
        return msg
    stop_event.clear()
    output_file = os.path.join(output_folder, "merged_output.txt")
    try:
        with open(output_file, "w", encoding="utf-8") as outfile:
            first_file = True
            for fname in os.listdir(input_folder):
                if stop_event.is_set():
                    return "Process stopped by user."
                if fname.lower().endswith(".txt"):
                    path = os.path.join(input_folder, fname)
                    with open(path, "r", encoding="utf-8") as f:
                        data = f.read()
                    if not first_file:
                        outfile.write("\n\n")
                    outfile.write(data)
                    first_file = False
        return f"All text files have been merged into: {output_file}"
    except Exception as e:
        return f"Error: {str(e)}"


def convert_images(input_folder, output_folder, old_format, new_format, jpg_quality, png_compression):
    """
    Convert images by opening them with Pillow (or imageio for RAW/animated formats)
    and saving them in the new format. Uses JPEG quality and PNG compression settings.
    """
    valid, msg = check_output_empty(output_folder)
    if not valid:
        return msg

    stop_event.clear()
    old_ext = old_format.lower()
    new_ext = new_format.lower()
    processed_any = False

    # List of RAW formats supported via imageio
    raw_formats = ["cr2", "nef", "arw", "dng"]

    try:
        for fname in os.listdir(input_folder):
            if stop_event.is_set():
                return "Process stopped by user."
            if fname.lower().endswith(f".{old_ext}"):
                source = os.path.join(input_folder, fname)
                base = os.path.splitext(fname)[0]
                new_name = base + "." + new_ext
                target = os.path.join(output_folder, new_name)
                # Use imageio for RAW images or if improved handling for GIF/WebP is desired
                if old_ext in raw_formats:
                    if iio is not None:
                        arr = iio.imread(source)
                        im = Image.fromarray(arr)
                    else:
                        continue  # Skip if imageio not available
                elif old_ext in ["gif", "webp"] and iio is not None:
                    # Use imageio to read the first frame
                    arr = iio.imread(source)
                    if isinstance(arr, list) and len(arr) > 0:
                        im = Image.fromarray(arr[0])
                    else:
                        im = Image.fromarray(arr)
                else:
                    im = Image.open(source)
                # Convert & save in new format
                if new_ext in ["jpg", "jpeg"]:
                    im = im.convert("RGB")
                    im.save(target, format="JPEG", quality=int(jpg_quality))
                elif new_ext == "png":
                    im.save(target, format="PNG", compress_level=int(png_compression))
                else:
                    im.save(target, format=new_ext.upper())
                processed_any = True
        if not processed_any:
            return f"No files found with the extension '{old_ext}'."
        else:
            return f"All .{old_ext} images converted to .{new_ext} in {output_folder}."
    except Exception as e:
        return f"Error: {str(e)}"


def split_jsonl(input_file, output_folder, lines_per_file):
    valid, msg = check_output_empty(output_folder)
    if not valid:
        return msg
    stop_event.clear()
    try:
        lines_per_file = int(lines_per_file)
    except ValueError:
        return "Please enter a valid integer for lines per file."
    if not os.path.isfile(input_file):
        return f"Input file does not exist: {input_file}"
    count = 0
    file_count = 1
    outfile_path = os.path.join(output_folder, f"split_{file_count}.txt")
    try:
        outfile = open(outfile_path, "w", encoding="utf-8")
        with open(input_file, "r", encoding="utf-8") as infile:
            for line in infile:
                if stop_event.is_set():
                    outfile.close()
                    return "Process stopped by user."
                if not any(ch.isdigit() for ch in line):
                    outfile.write(line.rstrip("\n") + "\n\n")
                    count += 2
                    if count >= lines_per_file:
                        outfile.close()
                        file_count += 1
                        outfile_path = os.path.join(output_folder, f"split_{file_count}.txt")
                        outfile = open(outfile_path, "w", encoding="utf-8")
                        count = 0
        outfile.close()
        return f"Processing complete. Created {file_count} file(s)."
    except Exception as e:
        return f"Error: {str(e)}"


def remove_duplicates(input_file, output_folder):
    valid, msg = check_output_empty(output_folder)
    if not valid:
        return msg
    stop_event.clear()
    if not os.path.isfile(input_file):
        return f"Input file does not exist: {input_file}"
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        original_count = len(lines)
        seen = set()
        unique_lines = []
        for line in lines:
            if stop_event.is_set():
                return "Process stopped by user."
            if line not in seen:
                seen.add(line)
                unique_lines.append(line)
        removed_count = original_count - len(unique_lines)
        base = os.path.basename(input_file)
        name, ext = os.path.splitext(base)
        output_file = os.path.join(output_folder, f"{name}_purged{ext}")
        with open(output_file, "w", encoding="utf-8") as f:
            f.writelines(unique_lines)
        return f"Duplicate records removed: {removed_count}\nOutput file: {output_file}"
    except Exception as e:
        return f"Error: {str(e)}"


def split_large_text(input_file, output_folder, lines_per_file):
    valid, msg = check_output_empty(output_folder)
    if not valid:
        return msg
    stop_event.clear()
    try:
        lines_per_file = int(lines_per_file)
    except ValueError:
        return "Please enter a valid integer for lines per file."
    if not os.path.isfile(input_file):
        return f"Input file does not exist: {input_file}"
    count = 0
    file_count = 1
    outfile_path = os.path.join(output_folder, f"split_{file_count}.txt")
    try:
        outfile = open(outfile_path, "w", encoding="utf-8")
        with open(input_file, "r", encoding="utf-8") as infile:
            for line in infile:
                if stop_event.is_set():
                    outfile.close()
                    return "Process stopped by user."
                outfile.write(line.rstrip("\n") + "\n\n")
                count += 2
                if count >= lines_per_file:
                    outfile.close()
                    file_count += 1
                    outfile_path = os.path.join(output_folder, f"split_{file_count}.txt")
                    outfile = open(outfile_path, "w", encoding="utf-8")
                    count = 0
        outfile.close()
        return f"Splitting complete. Created {file_count} file(s)."
    except Exception as e:
        return f"Error: {str(e)}"


# --------------------------------------------------------------------------------
# Dynamic UI update for Image Format Converter settings
# --------------------------------------------------------------------------------

def update_conversion_settings(out_format):
    """
    Update the visibility of conversion settings based on the selected output format.
    Shows the JPEG Quality slider if JPEG is selected, PNG Compression slider if PNG is selected.
    """
    out_format = out_format.lower()
    if out_format in ["jpg", "jpeg"]:
        return gr.update(visible=True), gr.update(visible=False)
    elif out_format == "png":
        return gr.update(visible=False), gr.update(visible=True)
    else:
        return gr.update(visible=False), gr.update(visible=False)


# --------------------------------------------------------------------------------
# GRADIO UI
# --------------------------------------------------------------------------------

def build_ui():
    with gr.Blocks() as demo:
        gr.Markdown("# DataSet Batch Processor")
        with gr.Tabs():
            # --- TAB 1: TILING ---
            with gr.Tab("Tiling"):
                gr.Markdown("**Image Tiling & Manual Captioning**")
                with gr.Row():
                    folder_input = gr.Textbox(label="Input Image Folder")
                    output_path_input = gr.Textbox(label="Output Folder (must be empty)")
                with gr.Row():
                    tile_size_input = gr.Number(value=1024, label="Tile Size (pixels)")
                    overlap_ratio_input = gr.Slider(0, 1, value=0.5, step=0.1, label="Overlap Ratio")
                    padding_input = gr.Number(value=10, label="Padding (pixels)")
                    num_tiles_input = gr.Number(value=0, label="Number of Tiles (0 = Use Tile Size)")
                caption_text_input = gr.Textbox(label="Manual Caption (Optional)")
                output_format_input = gr.Radio(choices=["None", "JPG", "PNG"], value="None", label="Output Image Format")
                tile_btn = gr.Button("Process Images")
                stop_tile_btn = gr.Button("Stop")
                tile_output = gr.Textbox(label="Status", interactive=False)
                tile_gallery = gr.Gallery(label="Tiled Images", show_label=False, height=400)
                zip_btn = gr.Button("Download Processed Tiles")
                zip_output = gr.File(label="ZIP File")
                tile_btn.click(on_tiling, inputs=[folder_input, tile_size_input, overlap_ratio_input, padding_input, num_tiles_input, caption_text_input, output_path_input, output_format_input], outputs=[tile_output, tile_gallery])
                stop_tile_btn.click(stop_process, outputs=tile_output)
                zip_btn.click(create_zip, inputs=output_path_input, outputs=zip_output)
                
            # --- TAB 2: Merge Text Files ---
            with gr.Tab("Merge Text Files"):
                with gr.Row():
                    in_merge = gr.Textbox(label="Input Folder (with .txt files)")
                    out_merge = gr.Textbox(label="Output Folder (must be empty)")
                merge_btn = gr.Button("Process")
                stop_merge_btn = gr.Button("Stop")
                merge_output = gr.Textbox(label="Status", interactive=False)
                merge_btn.click(merge_text_files, inputs=[in_merge, out_merge], outputs=merge_output)
                stop_merge_btn.click(stop_process, outputs=merge_output)
                
            # --- TAB 3: Image Format Converter ---
            with gr.Tab("Image Format Converter"):
                with gr.Row():
                    in_conv = gr.Textbox(label="Input Folder")
                    out_conv = gr.Textbox(label="Output Folder (must be empty)")
                with gr.Row():
                    old_format_dropdown = gr.Dropdown(choices=["jpg", "png", "bmp", "tiff", "gif", "webp", "heic", "cr2", "nef", "arw", "dng"], label="Input Format", value="jpg")
                    new_format_dropdown = gr.Dropdown(choices=["jpg", "png", "bmp", "tiff", "gif", "webp"], label="Output Format", value="jpg")
                # Dynamic sliders: JPEG quality and PNG compression level.
                jpg_quality_slider = gr.Slider(minimum=1, maximum=100, value=85, label="JPEG Quality", visible=True)
                png_compression_slider = gr.Slider(minimum=0, maximum=9, value=6, label="PNG Compression Level", visible=False)
                conv_btn = gr.Button("Process")
                stop_conv_btn = gr.Button("Stop")
                conv_output = gr.Textbox(label="Status", interactive=False)
                # Update dynamic UI when output format changes
                new_format_dropdown.change(update_conversion_settings, inputs=new_format_dropdown, outputs=[jpg_quality_slider, png_compression_slider])
                conv_btn.click(convert_images, inputs=[in_conv, out_conv, old_format_dropdown, new_format_dropdown, jpg_quality_slider, png_compression_slider], outputs=conv_output)
                stop_conv_btn.click(stop_process, outputs=conv_output)
                
            # --- TAB 4: Split JSONL File ---
            with gr.Tab("Split JSONL File"):
                with gr.Row():
                    in_jsonl = gr.Textbox(label="Input JSONL File")
                    out_jsonl = gr.Textbox(label="Output Folder (must be empty)")
                lines_jsonl = gr.Textbox(label="Number of lines per file", value="100")
                jsonl_btn = gr.Button("Process")
                stop_jsonl_btn = gr.Button("Stop")
                jsonl_output = gr.Textbox(label="Status", interactive=False)
                jsonl_btn.click(split_jsonl, inputs=[in_jsonl, out_jsonl, lines_jsonl], outputs=jsonl_output)
                stop_jsonl_btn.click(stop_process, outputs=jsonl_output)
                
            # --- TAB 5: Remove Duplicates From Text File---
            with gr.Tab("Remove Duplicates"):
                with gr.Row():
                    in_dup = gr.Textbox(label="Input File (with .txt files)")
                    out_dup = gr.Textbox(label="Output Folder (must be empty)")
                dup_btn = gr.Button("Process")
                stop_dup_btn = gr.Button("Stop")
                dup_output = gr.Textbox(label="Status", interactive=False)
                dup_btn.click(remove_duplicates, inputs=[in_dup, out_dup], outputs=dup_output)
                stop_dup_btn.click(stop_process, outputs=dup_output)
                
            # --- TAB 6: Split Large Text File ---
            with gr.Tab("Split Large Text File"):
                with gr.Row():
                    in_split = gr.Textbox(label="Input Text File")
                    out_split = gr.Textbox(label="Output Folder (must be empty)")
                lines_split = gr.Textbox(label="Number of lines per file", value="100")
                split_btn = gr.Button("Process")
                stop_split_btn = gr.Button("Stop")
                split_output = gr.Textbox(label="Status", interactive=False)
                split_btn.click(split_large_text, inputs=[in_split, out_split, lines_split], outputs=split_output)
                stop_split_btn.click(stop_process, outputs=split_output)
                
        gr.Markdown(
            """
            ---
            **Disclaimer**: I am not responsible for any data loss, damage, or other issues that may arise from its use. Please use it at your own risk and ensure you have proper backups before proceeding.  
            **Credits**: Eagle-42  
            """
        )
    return demo


if __name__ == "__main__":
    demo = build_ui()
    demo.launch(server_name="127.0.0.1", server_port=7864, inbrowser=True)

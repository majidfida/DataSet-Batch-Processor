import os
import shutil
import zipfile
import threading

import gradio as gr
from PIL import Image
from tqdm import tqdm
import numpy as np  # Needed for padding

# Enable HEIC/HEIF support if pillow_heif is installed
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
        return False, f"Output folder is not empty: {output_folder}"
    return True, ""

# -----------------------------------------------------------------------------
# Helper for Recommended Crop Dimensions
# -----------------------------------------------------------------------------

def compute_recommended_crop(width, height, tile_size, step):
    """
    Returns the recommended (new_width, new_height) to ensure 1:1 tileability.
    Calculation is based on the top-left crop.
    """
    if width < tile_size or height < tile_size:
        return (width, height)
    new_width = ((width - tile_size) // step) * step + tile_size
    new_height = ((height - tile_size) // step) * step + tile_size
    new_width = min(new_width, width)
    new_height = min(new_height, height)
    return (new_width, new_height)

def _write_recommended_crop_text(image_path, rec_width, rec_height):
    """
    Creates a .txt file alongside the moved image with recommended crop dimensions.
    For example, for "image.jpg", creates "image.txt".
    """
    base_name, _ = os.path.splitext(image_path)
    txt_path = base_name + ".txt"
    try:
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"Recommended crop size: {rec_width} x {rec_height}\n")
            f.write("Manually crop (preferably center-crop) to these dimensions for 1:1 tiling.\n")
            f.write("If that removes important areas, consider a manual approach.\n")
        print(f"Text file written: {txt_path}")
    except Exception as e:
        print(f"Error writing text file {txt_path}: {e}")

# -----------------------------------------------------------------------------
# Filter & Auto-Crop Code
# -----------------------------------------------------------------------------

def filter_incompatible_images(input_folder, incompatible_folder, tile_size, overlap_ratio, padding):
    """
    Moves images from input_folder to incompatible_folder if they cannot be tiled into
    exact 1:1 squares. Also writes a .txt file with recommended crop size.
    """
    if not os.path.isdir(input_folder):
        return f"Input folder does not exist: {input_folder}"
    os.makedirs(incompatible_folder, exist_ok=True)
    
    step = tile_size - int(overlap_ratio * tile_size)
    moved_count = 0
    stop_event.clear()

    for fname in os.listdir(input_folder):
        if stop_event.is_set():
            return "Process stopped by user."
        if not fname.lower().endswith((".png", ".jpg", ".jpeg", ".heic", ".cr2", ".nef", ".arw", ".dng")):
            continue
        
        src_path = os.path.join(input_folder, fname)
        try:
            # Open and immediately close the image to release any file locks
            im = Image.open(src_path)
            width, height = im.size
            im.close()

            # If the image is smaller than tile_size in either dimension, mark it incompatible
            if width < tile_size or height < tile_size:
                dst = os.path.join(incompatible_folder, fname)
                print(f"Moving {src_path} to {dst} (smaller than tile_size)")
                shutil.move(src_path, dst)
                moved_count += 1
                rec_width, rec_height = compute_recommended_crop(width, height, tile_size, step)
                _write_recommended_crop_text(dst, rec_width, rec_height)
                continue

            # Check alignment for perfect tiling
            if ((width - tile_size) % step != 0) or ((height - tile_size) % step != 0):
                dst = os.path.join(incompatible_folder, fname)
                print(f"Moving {src_path} to {dst} (dimensions not tileable)")
                shutil.move(src_path, dst)
                moved_count += 1
                rec_width, rec_height = compute_recommended_crop(width, height, tile_size, step)
                _write_recommended_crop_text(dst, rec_width, rec_height)
        except Exception as e:
            print(f"Error processing {fname}: {e}")

    return f"Moved {moved_count} incompatible images to: {incompatible_folder}"

def auto_crop_images(incompatible_folder, cropped_folder, tile_size, overlap_ratio, padding):
    """
    Crops each image in incompatible_folder so that it becomes compatible for 1:1 tiling.
    The auto-crop function adjusts the original image dimensions so that slicing produces perfect 1:1 tiles.
    This crop is performed from the center.
    Cropped images are saved to cropped_folder.
    """
    if not os.path.isdir(incompatible_folder):
        return f"Incompatible folder does not exist: {incompatible_folder}"
    valid, msg = check_output_empty(cropped_folder)
    if not valid:
        return msg
    os.makedirs(cropped_folder, exist_ok=True)

    step = tile_size - int(overlap_ratio * tile_size)
    cropped_count = 0
    stop_event.clear()

    for fname in os.listdir(incompatible_folder):
        if stop_event.is_set():
            return "Process stopped by user."
        if not fname.lower().endswith((".png", ".jpg", ".jpeg", ".heic", ".cr2", ".nef", ".arw", ".dng")):
            continue

        src_path = os.path.join(incompatible_folder, fname)
        try:
            with Image.open(src_path) as im:
                width, height = im.size
                new_width, new_height = compute_recommended_crop(width, height, tile_size, step)
                # Center crop coordinates
                left = (width - new_width) // 2
                top = (height - new_height) // 2
                cropped_im = im.crop((left, top, left + new_width, top + new_height))
                dst_path = os.path.join(cropped_folder, fname)
                cropped_im.save(dst_path)
                print(f"Cropped {fname}: ({new_width} x {new_height}) saved to {dst_path}")
                cropped_count += 1
        except Exception as e:
            print(f"Error cropping {fname}: {e}")

    return f"Auto-cropped {cropped_count} images into: {cropped_folder}"

def on_filter_incompatible(input_folder, incompatible_folder, tile_size, overlap_ratio, padding):
    return filter_incompatible_images(input_folder, incompatible_folder, tile_size, overlap_ratio, padding)

def on_auto_crop(incompatible_folder, cropped_folder, tile_size, overlap_ratio, padding):
    return auto_crop_images(incompatible_folder, cropped_folder, tile_size, overlap_ratio, padding)

# -----------------------------------------------------------------------------
# Tiling Code
# -----------------------------------------------------------------------------

def ensure_output_folder(path):
    os.makedirs(path, exist_ok=True)

def pad_tile_extend_edges(tile, tile_size):
    current_width, current_height = tile.size
    tile_array = np.array(tile)
    pad_right = tile_size - current_width
    pad_bottom = tile_size - current_height
    padded_array = np.pad(tile_array, ((0, pad_bottom), (0, pad_right), (0, 0)), mode='edge')
    return Image.fromarray(padded_array)

def tile_image(image_path, tile_size, overlap_ratio, padding, num_tiles, caption_text, output_path, output_format, pad_option):
    if stop_event.is_set():
        return []

    image = Image.open(image_path)
    image_width, image_height = image.size
    ensure_output_folder(output_path)

    if num_tiles:
        tile_size = min(image_width, image_height) // int(num_tiles ** 0.5)

    step = tile_size - int(overlap_ratio * tile_size)
    horizontal_tiles = max(0, (image_width - padding) // step)
    vertical_tiles = max(0, (image_height - padding) // step)

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

            if pad_option == "Auto Adjust":
                if (right - left) < tile_size:
                    left = max(image_width - tile_size, 0)
                    right = left + tile_size
                if (lower - upper) < tile_size:
                    upper = max(image_height - tile_size, 0)
                    lower = upper + tile_size

            tile_im = image.crop((left, upper, right, lower))

            if pad_option == "Extend Edges":
                w, h = tile_im.size
                if w != tile_size or h != tile_size:
                    tile_im = pad_tile_extend_edges(tile_im, tile_size)
            elif pad_option == "Pad to Square":
                w, h = tile_im.size
                if w != tile_size or h != tile_size:
                    new_tile = Image.new("RGB", (tile_size, tile_size), color=(0, 0, 0))
                    new_tile.paste(tile_im, (0, 0))
                    tile_im = new_tile

            base_name = os.path.splitext(os.path.basename(image_path))[0]
            file_extension = "jpg" if save_format == "JPEG" else "png"
            tile_filename = f"{base_name}_tile_{i}_{j}.{file_extension}"
            tile_path = os.path.join(output_path, tile_filename)
            tile_im.save(tile_path, format=save_format)
            tile_paths.append(tile_path)

            if caption_text:
                caption_filename = f"{base_name}_tile_{i}_{j}.txt"
                caption_path = os.path.join(output_path, caption_filename)
                with open(caption_path, "w", encoding="utf-8") as f:
                    f.write(caption_text)
    return tile_paths

def process_images_from_folder(folder_path, tile_size, overlap_ratio, padding, num_tiles, caption_text, output_path, output_format, pad_option):
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
                tile_paths = tile_image(image_path, tile_size, overlap_ratio, padding, num_tiles,
                                          caption_text, output_path, output_format, pad_option)
                all_tile_paths.extend(tile_paths)
                if stop_event.is_set():
                    return "Process stopped by user.", all_tile_paths
        return f"Tiling complete! {len(all_tile_paths)} tiles created.", all_tile_paths
    except Exception as e:
        return f"Error: {str(e)}", []

def create_zip(output_path):
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

def on_tiling(folder_path, tile_size, overlap_ratio, padding, num_tiles, caption_text, output_path, output_format, pad_option):
    message, tile_paths = process_images_from_folder(
        folder_path, tile_size, overlap_ratio, padding, num_tiles,
        caption_text, output_path, output_format, pad_option
    )
    return message, tile_paths

# -----------------------------------------------------------------------------
# Other Task Functions
# -----------------------------------------------------------------------------

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
    valid, msg = check_output_empty(output_folder)
    if not valid:
        return msg
    stop_event.clear()
    old_ext = old_format.lower()
    new_ext = new_format.lower()
    processed_any = False
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
                if old_ext in raw_formats:
                    if iio is not None:
                        arr = iio.imread(source)
                        im = Image.fromarray(arr)
                    else:
                        continue
                elif old_ext in ["gif", "webp"] and iio is not None:
                    arr = iio.imread(source)
                    if isinstance(arr, list) and len(arr) > 0:
                        im = Image.fromarray(arr[0])
                    else:
                        im = Image.fromarray(arr)
                else:
                    im = Image.open(source)
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
        return f"Processing complete. Created {file_count} file(s)."
    except Exception as e:
        return f"Error: {str(e)}"

def update_conversion_settings(out_format):
    out_format = out_format.lower()
    if out_format in ["jpg", "jpeg"]:
        return gr.update(visible=True), gr.update(visible=False)
    elif out_format == "png":
        return gr.update(visible=False), gr.update(visible=True)
    else:
        return gr.update(visible=False), gr.update(visible=False)

# -----------------------------------------------------------------------------
# GRADIO UI
# -----------------------------------------------------------------------------

def build_ui():
    with gr.Blocks() as demo:
        gr.Markdown("# DataSet Batch Processor")
        with gr.Tabs():
            # TAB 1: Tiling with Sub-Tabs
            with gr.Tab("Tiling"):
                with gr.Tabs():
                    # Sub-Tab A: Prepare Images for Tiling
                    with gr.Tab("Prepare Images for Tiling"):
                        gr.Markdown("**Filter & Auto-Crop**")
                        with gr.Row():
                            folder_input = gr.Textbox(label="Input Folder")
                            incompatible_path_input = gr.Textbox(label="Incompatible Folder")
                            cropped_path_input = gr.Textbox(label="Cropped Folder (must be empty)")
                        with gr.Row():
                            tile_size_input = gr.Number(value=1024, label="Tile Size (pixels)")
                            overlap_ratio_input = gr.Slider(0, 1, value=0.5, step=0.1, label="Overlap Ratio")
                            padding_input = gr.Number(value=10, label="Padding (pixels)")
                        filter_btn = gr.Button("Filter Incompatible")
                        auto_crop_btn = gr.Button("Auto Crop")
                        prep_status = gr.Textbox(label="Status", interactive=False)
                        stop_prep_btn = gr.Button("Stop")
                        filter_btn.click(
                            on_filter_incompatible,
                            inputs=[folder_input, incompatible_path_input, tile_size_input, overlap_ratio_input, padding_input],
                            outputs=prep_status
                        )
                        auto_crop_btn.click(
                            on_auto_crop,
                            inputs=[incompatible_path_input, cropped_path_input, tile_size_input, overlap_ratio_input, padding_input],
                            outputs=prep_status
                        )
                        stop_prep_btn.click(stop_process, outputs=prep_status)
                        gr.Markdown("""
                        **Steps:**  
                        1. Click **Filter Incompatible** to move images that would produce partial tiles into the **Incompatible Folder**.  
                           A text file with recommended crop dimensions is created for each moved image.
                        2. Optionally, click **Auto Crop** to center-crop those images (adjusting the original dimensions so that slicing produces perfect 1:1 tiles) and save them in the **Cropped Folder**.
                        3. If auto-cropping removes important areas, use the recommended dimensions in the text file to crop manually.
                        4. Once your images are prepared (either remaining in the Input Folder or from the Cropped Folder), proceed to the **Tile Images** tab.
                        """)
                    # Sub-Tab B: Tile Images
                    with gr.Tab("Tile Images"):
                        gr.Markdown("**Perform the Actual Tiling**")
                        with gr.Row():
                            tile_input_folder = gr.Textbox(label="Input Folder (for Tiling)")
                            tile_output_folder = gr.Textbox(label="Tiled Output Folder (must be empty)")
                        with gr.Row():
                            tile_size_input2 = gr.Number(value=1024, label="Tile Size (pixels)")
                            overlap_ratio_input2 = gr.Slider(0, 1, value=0.5, step=0.1, label="Overlap Ratio")
                            padding_input2 = gr.Number(value=10, label="Padding (pixels)")
                            num_tiles_input = gr.Number(value=0, label="Number of Tiles (0 = Use Tile Size)")
                        pad_option_dropdown = gr.Dropdown(
                            choices=["None", "Extend Edges", "Auto Adjust", "Pad to Square"],
                            value="None",
                            label="Pad Option"
                        )
                        caption_text_input = gr.Textbox(label="Manual Caption (Optional)")
                        output_format_input = gr.Radio(choices=["None", "JPG", "PNG"],
                                                       value="None",
                                                       label="Output Image Format")
                        tile_btn = gr.Button("Process Images")
                        tile_stop_btn = gr.Button("Stop")
                        tile_status = gr.Textbox(label="Status", interactive=False)
                        tile_gallery = gr.Gallery(label="Tiled Images", show_label=False, height=400)
                        zip_btn = gr.Button("Download Processed Tiles")
                        zip_output = gr.File(label="ZIP File")
                        tile_btn.click(
                            on_tiling,
                            inputs=[tile_input_folder, tile_size_input2, overlap_ratio_input2, padding_input2,
                                    num_tiles_input, caption_text_input, tile_output_folder,
                                    output_format_input, pad_option_dropdown],
                            outputs=[tile_status, tile_gallery]
                        )
                        tile_stop_btn.click(stop_process, outputs=tile_status)
                        zip_btn.click(create_zip, inputs=tile_output_folder, outputs=zip_output)
            # TAB 2: Merge Text Files
            with gr.Tab("Merge Text Files"):
                with gr.Row():
                    in_merge = gr.Textbox(label="Input Folder (with .txt files)")
                    out_merge = gr.Textbox(label="Output Folder (must be empty)")
                merge_btn = gr.Button("Process")
                stop_merge_btn = gr.Button("Stop")
                merge_output = gr.Textbox(label="Status", interactive=False)
                merge_btn.click(merge_text_files, inputs=[in_merge, out_merge], outputs=merge_output)
                stop_merge_btn.click(stop_process, outputs=merge_output)
            # TAB 3: Image Format Converter
            with gr.Tab("Image Format Converter"):
                with gr.Row():
                    in_conv = gr.Textbox(label="Input Folder")
                    out_conv = gr.Textbox(label="Output Folder (must be empty)")
                with gr.Row():
                    old_format_dropdown = gr.Dropdown(choices=["jpg", "png", "bmp", "tiff", "gif", "webp", "heic", "cr2", "nef", "arw", "dng"],
                                                      label="Input Format", value="jpg")
                    new_format_dropdown = gr.Dropdown(choices=["jpg", "png", "bmp", "tiff", "gif", "webp"],
                                                      label="Output Format", value="jpg")
                jpg_quality_slider = gr.Slider(minimum=1, maximum=100, value=85, label="JPEG Quality", visible=True)
                png_compression_slider = gr.Slider(minimum=0, maximum=9, value=6, label="PNG Compression Level", visible=False)
                conv_btn = gr.Button("Process")
                stop_conv_btn = gr.Button("Stop")
                conv_output = gr.Textbox(label="Status", interactive=False)
                new_format_dropdown.change(update_conversion_settings, inputs=new_format_dropdown,
                                           outputs=[jpg_quality_slider, png_compression_slider])
                conv_btn.click(convert_images, inputs=[in_conv, out_conv, old_format_dropdown, new_format_dropdown,
                                                       jpg_quality_slider, png_compression_slider],
                                outputs=conv_output)
                stop_conv_btn.click(stop_process, outputs=conv_output)
            # TAB 4: Split JSONL File
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
            # TAB 5: Remove Duplicates From Text File
            with gr.Tab("Remove Duplicates"):
                with gr.Row():
                    in_dup = gr.Textbox(label="Input File (with .txt files)")
                    out_dup = gr.Textbox(label="Output Folder (must be empty)")
                dup_btn = gr.Button("Process")
                stop_dup_btn = gr.Button("Stop")
                dup_output = gr.Textbox(label="Status", interactive=False)
                dup_btn.click(remove_duplicates, inputs=[in_dup, out_dup], outputs=dup_output)
                stop_dup_btn.click(stop_process, outputs=dup_output)
            # TAB 6: Split Large Text File
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
        gr.Markdown("""
        ---
        **Disclaimer:** Use at your own risk; always keep backups.
        **Credits:** Eagle-42
        """)
    return demo

if __name__ == "__main__":
    demo = build_ui()
    demo.launch(server_name="127.0.0.1", server_port=7868, inbrowser=True, allowed_paths=[os.getcwd()])

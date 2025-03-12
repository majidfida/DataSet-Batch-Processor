import os
import shutil
import zipfile
from PIL import Image
from tqdm import tqdm
import numpy as np
from modules.utils import check_output_empty

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
    for j in tqdm(range(vertical_tiles), desc=f"Tiling rows of {os.path.basename(image_path)}", unit="row"):
        for i in range(horizontal_tiles):
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
    if not os.path.isdir(folder_path):
        return "Invalid input folder path.", []
    all_tile_paths = []
    try:
        for filename in os.listdir(folder_path):
            if filename.lower().endswith((".png", ".jpg", ".jpeg", ".heic", ".cr2", ".nef", ".arw", ".dng")):
                image_path = os.path.join(folder_path, filename)
                tile_paths = tile_image(image_path, tile_size, overlap_ratio, padding, num_tiles,
                                          caption_text, output_path, output_format, pad_option)
                all_tile_paths.extend(tile_paths)
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

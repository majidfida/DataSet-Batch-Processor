import os
import shutil
from PIL import Image
from modules.utils import stop_event

def compute_recommended_crop(width, height, tile_size, step):
    if width < tile_size or height < tile_size:
        return (width, height)
    new_width = ((width - tile_size) // step) * step + tile_size
    new_height = ((height - tile_size) // step) * step + tile_size
    new_width = min(new_width, width)
    new_height = min(new_height, height)
    return (new_width, new_height)

def _write_recommended_crop_text(image_path, rec_width, rec_height):
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

def filter_incompatible_images(input_folder, incompatible_folder, tile_size, overlap_ratio, padding):
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
            im = Image.open(src_path)
            width, height = im.size
            im.close()

            if width < tile_size or height < tile_size:
                dst = os.path.join(incompatible_folder, fname)
                print(f"Moving {fname} (smaller than tile_size)")
                shutil.move(src_path, dst)
                moved_count += 1
                rec_width, rec_height = compute_recommended_crop(width, height, tile_size, step)
                _write_recommended_crop_text(dst, rec_width, rec_height)
                continue

            if ((width - tile_size) % step != 0) or ((height - tile_size) % step != 0):
                dst = os.path.join(incompatible_folder, fname)
                print(f"Moving {fname} (dimensions not tileable)")
                shutil.move(src_path, dst)
                moved_count += 1
                rec_width, rec_height = compute_recommended_crop(width, height, tile_size, step)
                _write_recommended_crop_text(dst, rec_width, rec_height)
        except Exception as e:
            print(f"Error processing {fname}: {e}")

    return f"Moved {moved_count} incompatible images to: {incompatible_folder}"

def auto_crop_images(incompatible_folder, cropped_folder, tile_size, overlap_ratio, padding):
    if not os.path.isdir(incompatible_folder):
        return f"Incompatible folder does not exist: {incompatible_folder}"
    from modules.utils import check_output_empty
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
                left = (width - new_width) // 2
                top = (height - new_height) // 2
                cropped_im = im.crop((left, top, left + new_width, top + new_height))
                dst_path = os.path.join(cropped_folder, fname)
                cropped_im.save(dst_path)
                print(f"Cropped {fname}: ({new_width} x {new_height}) saved")
                cropped_count += 1
        except Exception as e:
            print(f"Error cropping {fname}: {e}")

    return f"Auto-cropped {cropped_count} images into: {cropped_folder}"

def on_filter_incompatible(input_folder, incompatible_folder, tile_size, overlap_ratio, padding):
    return filter_incompatible_images(input_folder, incompatible_folder, tile_size, overlap_ratio, padding)

def on_auto_crop(incompatible_folder, cropped_folder, tile_size, overlap_ratio, padding):
    return auto_crop_images(incompatible_folder, cropped_folder, tile_size, overlap_ratio, padding)

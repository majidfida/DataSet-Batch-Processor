import os
import shutil
import zipfile
from modules.utils import stop_event, check_output_empty

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
            if fname.lower().endswith(f".{old_ext}"):
                source = os.path.join(input_folder, fname)
                base = os.path.splitext(fname)[0]
                new_name = base + "." + new_ext
                target = os.path.join(output_folder, new_name)
                from PIL import Image
                if old_ext in raw_formats:
                    try:
                        import imageio.v3 as iio
                    except ImportError:
                        continue
                    arr = iio.imread(source)
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

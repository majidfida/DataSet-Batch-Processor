import os
import shutil
from tqdm import tqdm
import cv2
from mtcnn import MTCNN
from modules.utils import stop_event

def skip_background_tiles(tile_folder, skip_folder):
    """
    Scans the tile_folder for images and uses MTCNN to detect faces.
    If no faces (or only very low-confidence detections) are found, moves the image and its
    corresponding text file to the skip_folder.
    A stop check is performed on each iteration.
    """
    if not os.path.isdir(tile_folder):
        return "Tile folder does not exist."
    os.makedirs(skip_folder, exist_ok=True)
    detector = MTCNN()
    files = [f for f in os.listdir(tile_folder) if f.lower().endswith((".png", ".jpg", ".jpeg"))]
    moved_count = 0
    for fname in tqdm(files, desc="Skipping background tiles", unit="file"):
        if stop_event.is_set():
            return "Process stopped by user."
        file_path = os.path.join(tile_folder, fname)
        img = cv2.imread(file_path)
        if img is None or img.size == 0:
            continue
        try:
            faces = detector.detect_faces(img)
        except Exception as e:
            print(f"Error detecting faces in {fname}: {e}")
            continue
        # Consider face detection valid if any face has confidence above 0.95
        if not any(face.get("confidence", 0) >= 0.95 for face in faces):
            dst_path = os.path.join(skip_folder, fname)
            try:
                shutil.move(file_path, dst_path)
                moved_count += 1
            except Exception as e:
                print(f"Error moving {fname}: {e}")
            base, _ = os.path.splitext(fname)
            txt_file = base + ".txt"
            txt_path = os.path.join(tile_folder, txt_file)
            if os.path.exists(txt_path):
                try:
                    shutil.move(txt_path, os.path.join(skip_folder, txt_file))
                except Exception as e:
                    print(f"Error moving text file {txt_file}: {e}")
    return f"Moved {moved_count} background-heavy tiles to {skip_folder}."

def on_skip_background_tiles(tile_folder, skip_folder):
    return skip_background_tiles(tile_folder, skip_folder)

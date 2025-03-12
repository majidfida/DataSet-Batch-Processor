import os

CAPTIONS_FILE = "Unified_Caps.txt"

def load_captions():
    if not os.path.exists(CAPTIONS_FILE):
        return []
    with open(CAPTIONS_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    # Return a list of non-empty lines
    captions = [line.strip() for line in lines if line.strip()]
    return captions

def save_caption(new_caption):
    new_caption = new_caption.strip()
    if not new_caption:
        return load_captions()
    captions = load_captions()
    # If it already exists, remove and re-insert so it goes to front
    if new_caption in captions:
        captions.remove(new_caption)
    captions.insert(0, new_caption)
    with open(CAPTIONS_FILE, "w", encoding="utf-8") as f:
        for cap in captions:
            f.write(cap + "\n")
    return captions

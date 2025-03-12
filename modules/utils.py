import os
import threading

stop_event = threading.Event()

def stop_process():
    """Signal any running process to stop."""
    stop_event.set()
    return "Stop request sent."

def check_output_empty(output_folder):
    if not os.path.isdir(output_folder):
        return False, f"Output folder does not exist: {output_folder}"
    if os.listdir(output_folder):
        return False, f"Output folder is not empty: {output_folder}"
    return True, ""

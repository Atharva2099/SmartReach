import threading
import queue
import time
import json
import cv2

from robotRecording import execute_positions  # Stub from robotRecording.py
from utils.gemini_api import process_image

# Load robot sequences from JSON file.
with open("robot_sequences.json") as f:
    # This builds a dictionary keyed by the "key" value in the JSON.
    sequences = {x["key"]: x for x in json.load(f)}

gemini_result_queue = queue.Queue()

def capture_image():
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    cap.release()
    if ret:
        return frame
    else:
        raise Exception("Camera error")

def go_to_position(pos_key):
    print(f"Moving to position {pos_key}")
    steps = sequences[pos_key]["positions"]
    for step in steps:
        execute_positions(step)
        time.sleep(0.1)

def gemini_thread(image, object_name, pos_id):
    result = process_image(image, object_name, pos_id)
    gemini_result_queue.put(result)

def main():
    print("System started. Moving to ACTIVE state.")
    go_to_position(1)  # ACTIVE state is assumed to be key 1
    state = 1
    visited = set()
    object_to_find = "bottle"

    while True:
        if state == 1:
            # Choose the next position to check (2, 4, 6).
            next_pos = [2, 4, 6]
            next_pos = [p for p in next_pos if p not in visited]
            if not next_pos:
                print("Object not found in any position.")
                break

            pos = next_pos[0]
            visited.add(pos)
            go_to_position(pos)
            frame = capture_image()
            # Start Gemini processing in a separate thread.
            threading.Thread(target=gemini_thread, args=(frame, object_to_find, pos)).start()
            state = 99  # Waiting for Gemini result

        elif state == 99:
            if not gemini_result_queue.empty():
                result = gemini_result_queue.get()
                if result["found"]:
                    print("Found! Executing pick and returning to ACTIVE.")
                    # Assuming the pick state is one position after the check.
                    go_to_position(pos + 1)
                    go_to_position(1)  # Return to ACTIVE state.
                    break
                else:
                    print("Not found at this position. Trying next.")
                    state = 1

if __name__ == "__main__":
    main()
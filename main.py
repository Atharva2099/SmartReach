import threading
import queue
import time
import json
import cv2
import sys
import os

# Import for MQTT integration
from utils.mqtt_client import start_mqtt_client, stop_mqtt_client, go_to_position, set_broker_address, client
from utils.gemini_api import process_image

# Determine if we should use MQTT (True) or local robot control (False)
USE_MQTT = True  # Set to False to use local robot control functions

# Load robot sequences from JSON file for local control mode
sequences = {}
if os.path.exists("robot_sequences.json"):
    with open("robot_sequences.json") as f:
        # This builds a dictionary keyed by the "key" value in the JSON.
        sequences = {x["key"]: x for x in json.load(f)}

# Import local robot control functions only if needed
if not USE_MQTT:
    from robotRecording import execute_positions

# Global queue for communication between threads
gemini_result_queue = queue.Queue()

def capture_image():
    """Capture an image from the webcam."""
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    cap.release()
    if ret:
        return frame
    else:
        raise Exception("Camera error")

def go_to_position_local(pos_key):
    """
    Local implementation of robot control (used when MQTT is disabled).
    Moves the robot to the specified position using local control.
    """
    print(f"Moving to position {pos_key}")
    if pos_key not in sequences:
        print(f"Error: Position {pos_key} not found in sequences")
        return False
    
    steps = sequences[pos_key]["positions"]
    try:
        for step in steps:
            execute_positions(step)
            time.sleep(0.1)
        return True
    except Exception as e:
        print(f"Error executing position: {e}")
        return False

def gemini_thread(image, object_name, pos_id=None):
    """
    Thread function to process image with Gemini API.
    
    Args:
        image: The captured image to analyze
        object_name: The name of the object to look for
        pos_id: Optional position ID for logging
    """
    prompt = f"Is there a {object_name} in this image? Respond with 'found' or 'not found' only."
    
    try:
        result_text = process_image(image, prompt)
        found = "found" in result_text.lower()
        print(f"Gemini result: {'Found' if found else 'Not found'} at position {pos_id}")
        
        result = {
            "found": found,
            "position": pos_id,
            "text": result_text
        }
        gemini_result_queue.put(result)
    except Exception as e:
        print(f"Error in Gemini processing: {e}")
        gemini_result_queue.put({"found": False, "error": str(e)})

def main():
    print("SmartReach System Starting")
    
    # Allow setting the broker IP from command line
    if len(sys.argv) > 1:
        broker_ip = sys.argv[1]
        set_broker_address(broker_ip)
        print(f"Using broker address: {broker_ip}")
    
    # Initialize MQTT if enabled
    if USE_MQTT:
        if not start_mqtt_client():
            print("Failed to start MQTT client. Exiting.")
            return
    
    print("System started. Moving to ACTIVE state.")
    # Choose the appropriate function based on mode
    position_func = go_to_position if USE_MQTT else go_to_position_local
    
    # Move to ACTIVE state (position 1)
    if not position_func(1):
        print("Failed to move to ACTIVE state. Exiting.")
        if USE_MQTT:
            stop_mqtt_client()
        return
    
    state = 1
    visited = set()
    object_to_find = "bottle"

    try:
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
                
                print(f"Moving to position {pos} to check for {object_to_find}...")
                success = position_func(pos)
                if not success:
                    print("Failed to move to position, retrying...")
                    time.sleep(2)  # Short delay before retry
                    continue
                
                print("Capturing image...")
                try:
                    frame = capture_image()
                    print("Processing with Gemini...")
                    # Start Gemini processing in a separate thread.
                    threading.Thread(target=gemini_thread, args=(frame, object_to_find, pos)).start()
                    state = 99  # Waiting for Gemini result
                except Exception as e:
                    print(f"Error during image capture: {e}")
                    state = 1  # Return to active state to try next position

            elif state == 99:
                if not gemini_result_queue.empty():
                    result = gemini_result_queue.get()
                    if "error" in result:
                        print(f"Error from Gemini thread: {result['error']}")
                        state = 1  # Try the next position
                        continue
                        
                    if result["found"]:
                        print(f"Found {object_to_find}! Executing pick operation.")
                        # Assuming the pick state is one position after the check.
                        pick_pos = pos + 1
                        success = position_func(pick_pos)
                        if success:
                            print("Pick operation completed. Returning to ACTIVE state.")
                            position_func(1)  # Return to ACTIVE state.
                            break
                        else:
                            print("Pick operation failed. Returning to ACTIVE state.")
                            position_func(1)
                            break
                    else:
                        print(f"{object_to_find} not found at position {pos}. Trying next position.")
                        state = 1
                else:
                    # Brief pause to prevent CPU spinning while waiting for Gemini result
                    time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    except Exception as e:
        print(f"\nError in main control loop: {e}")
    finally:
        # Try to return to a safe position
        print("Returning to ACTIVE state...")
        try:
            position_func(1)
        except:
            pass
            
        # Clean up MQTT client if enabled
        if USE_MQTT:
            stop_mqtt_client()
        
        print("System shutdown complete")

if __name__ == "__main__":
    main()
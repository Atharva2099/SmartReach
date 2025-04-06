import threading
import queue
import time
import json
import cv2
import os
import logging
from datetime import datetime

from robotRecording import execute_positions  # Now using our enhanced version
from utils.gemini_api import process_image, setup_gemini_api

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"robot_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load robot sequences from JSON file.
try:
    with open("robot_sequences.json") as f:
        # This builds a dictionary keyed by the "key" value in the JSON.
        sequences = {x["key"]: x for x in json.load(f)}
    logger.info(f"Loaded {len(sequences)} sequences from robot_sequences.json")
except Exception as e:
    logger.error(f"Failed to load robot_sequences.json: {str(e)}")
    raise

# Ensure Gemini API is set up
try:
    setup_gemini_api()
    logger.info("Gemini API setup completed")
except Exception as e:
    logger.error(f"Failed to set up Gemini API: {str(e)}")
    raise

# Global queue for thread communication
gemini_result_queue = queue.Queue()

def capture_image():
    """
    Capture an image from the camera.
    
    Returns:
        numpy.ndarray: The captured image, or None if capture failed
    
    Raises:
        Exception: If camera access fails
    """
    logger.info("Capturing image from camera")
    try:
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            # Save a copy of the image for debugging
            os.makedirs("captured_images", exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            cv2.imwrite(f"captured_images/capture_{timestamp}.jpg", frame)
            logger.info(f"Image captured and saved to captured_images/capture_{timestamp}.jpg")
            return frame
        else:
            logger.error("Camera returned no image")
            raise Exception("Camera returned no image")
    except Exception as e:
        logger.error(f"Camera error: {str(e)}")
        raise Exception(f"Camera error: {str(e)}")

def go_to_position(pos_key):
    """
    Move the robot to a specific position sequence.
    
    Args:
        pos_key: The key of the position sequence to execute
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info(f"Moving to position {pos_key}")
        if pos_key not in sequences:
            logger.error(f"Position key {pos_key} not found in sequences")
            return False
            
        steps = sequences[pos_key]["positions"]
        logger.info(f"Executing {len(steps)} steps for position {pos_key}")
        
        for i, step in enumerate(steps):
            logger.info(f"Step {i+1}/{len(steps)}: {step}")
            success = execute_positions(step)
            if not success:
                logger.warning(f"Step {i+1} execution reported failure")
            time.sleep(0.1)
        
        logger.info(f"Position {pos_key} execution completed")
        return True
    except Exception as e:
        logger.error(f"Error in go_to_position({pos_key}): {str(e)}")
        return False

def gemini_thread(image, object_name, pos_id):
    """
    Process an image with Gemini in a separate thread.
    
    Args:
        image: The image to analyze (NumPy array from OpenCV)
        object_name: The name of the object to look for (e.g., "bottle")
        pos_id: Position ID for context
    """
    logger.info(f"Starting Gemini analysis for object '{object_name}' at position {pos_id}")
    try:
        # Create a prompt specifically asking about the object
        prompt = f"Is there a {object_name} in this image?"
        
        # Call the process_image function with position ID
        result = process_image(image, prompt, pos_id)
        
        # Log the result summary
        logger.info(f"Gemini result for position {pos_id}: Found={result['found']}")
        logger.info(f"Gemini response: {result['text'][:100]}...")
        
        # Put the result in the queue for the main thread to process
        gemini_result_queue.put(result)
    except Exception as e:
        logger.error(f"Error in Gemini thread: {str(e)}")
        # Put a failure result in the queue so the main thread doesn't hang
        gemini_result_queue.put({
            "found": False,
            "text": f"Error in Gemini analysis: {str(e)}",
            "position": pos_id,
            "error": True
        })

def main():
    logger.info("System started")
    
    try:
        logger.info("Moving to ACTIVE state")
        if not go_to_position(1):  # ACTIVE state is assumed to be key 1
            logger.error("Failed to reach ACTIVE state")
            return
        
        state = 1
        visited = set()
        object_to_find = "bottle"  # This could be made configurable
        logger.info(f"Search initialized for object: {object_to_find}")
        
        while True:
            if state == 1:
                # Choose the next position to check (2, 4, 6)
                next_pos = [2, 4, 6]
                next_pos = [p for p in next_pos if p not in visited]
                
                if not next_pos:
                    logger.info("Object not found in any position. Search complete.")
                    break
                
                pos = next_pos[0]
                visited.add(pos)
                logger.info(f"Checking position {pos} (positions checked: {visited})")
                
                if not go_to_position(pos):
                    logger.error(f"Failed to reach position {pos}")
                    continue
                
                try:
                    frame = capture_image()
                    # Start Gemini processing in a separate thread
                    thread = threading.Thread(
                        target=gemini_thread, 
                        args=(frame, object_to_find, pos)
                    )
                    thread.start()
                    logger.info(f"Started Gemini analysis thread for position {pos}")
                    state = 99  # Waiting for Gemini result
                except Exception as e:
                    logger.error(f"Error during image capture: {str(e)}")
                    state = 1  # Stay in state 1 to try the next position
            
            elif state == 99:
                # Check if there's a result from Gemini
                if not gemini_result_queue.empty():
                    result = gemini_result_queue.get()
                    
                    # Check if there was an error in the Gemini thread
                    if result.get("error", False):
                        logger.error(f"Gemini thread reported an error: {result.get('text', 'Unknown error')}")
                        state = 1  # Move on to the next position
                        continue
                    
                    pos = result.get("position")
                    if result["found"]:
                        logger.info(f"Object found at position {pos}! Executing pick sequence.")
                        
                        # Assuming the pick state is one position after the check
                        pick_pos = pos + 1
                        if pick_pos in sequences:
                            if not go_to_position(pick_pos):
                                logger.error(f"Failed to execute pick sequence at position {pick_pos}")
                            else:
                                logger.info(f"Pick sequence at position {pick_pos} completed")
                        else:
                            logger.error(f"Pick position {pick_pos} not defined in sequences")
                        
                        # Return to ACTIVE state
                        if not go_to_position(1):
                            logger.error("Failed to return to ACTIVE state")
                        
                        logger.info("Task completed successfully")
                        break
                    else:
                        logger.info(f"Object not found at position {pos}. Trying next position.")
                        state = 1  # Go back to state 1 to try the next position
                else:
                    # Still waiting for Gemini, sleep a bit
                    time.sleep(0.1)
    
    except KeyboardInterrupt:
        logger.info("System interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error in main: {str(e)}")
    finally:
        # Ensure we end in a safe state
        try:
            logger.info("Returning to HOME state")
            go_to_position(0)  # Assuming 0 is HOME
        except Exception as e:
            logger.error(f"Error returning to HOME: {str(e)}")
        
        logger.info("System shutdown complete")

if __name__ == "__main__":
    main()
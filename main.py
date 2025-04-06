import time
import logging
import cv2
import random
from utils.gemini_api import process_image, setup_gemini_api
from utils.mqtt_client import start_mqtt_client, stop_mqtt_client, send_position_command

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    setup_gemini_api()
    start_mqtt_client()

    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        logger.error("Failed to capture image")
        stop_mqtt_client()
        return

    object_query = input("Enter the object to search for (e.g., bottle): ").strip()
    check_positions = [2, 4, 6]
    pick_map = {2: 3, 4: 5, 6: 7}
    found = False
    decision_text = ""
    
    for pos in random.sample(check_positions, len(check_positions)):
        send_position_command(pos)
        time.sleep(2)
        prompt = f"Is there a {object_query} in frame? Answer yes or no."
        decision_text = process_image(frame, prompt)
        logger.info(f"Gemini decision at check position {pos}: {decision_text}")
        if decision_text == "yes":
            send_position_command(pick_map[pos])
            time.sleep(5)
            found = True
            break
    if not found:
        send_position_command(1)
    
    time.sleep(2)
    stop_mqtt_client()

if __name__ == "__main__":
    main()
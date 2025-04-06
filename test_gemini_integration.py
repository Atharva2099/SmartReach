import cv2
from utils.gemini_api import process_image, setup_gemini_api

def main():
    # Initialize Gemini API (loads .env and sets API key)
    setup_gemini_api()
    
    # Capture an image from the webcam
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        print("Failed to capture image from webcam.")
        return
    
    # Provide a prompt to test Gemini processing
    prompt = "Describe this image in detail."
    
    # Process the captured image with Gemini
    result = process_image(frame, prompt)
    print("Gemini Response:")
    print(result)

if __name__ == "__main__":
    main()
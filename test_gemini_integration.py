import cv2
import os
import time
from datetime import datetime
from utils.gemini_api import process_image, setup_gemini_api

def test_gemini_object_detection():
    """
    Test the Gemini API's ability to detect objects in images.
    This script will capture an image from the webcam and ask Gemini if specific objects are present.
    """
    print("=== Gemini Object Detection Test ===")
    
    # Ensure Gemini API is configured
    try:
        setup_gemini_api()
        print("✓ Gemini API setup successful")
    except Exception as e:
        print(f"✗ Gemini API setup failed: {str(e)}")
        return
    
    # Capture an image
    try:
        print("Capturing image from webcam...")
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            print("✗ Failed to capture image from webcam")
            return
        
        # Save the image for reference
        os.makedirs("test_images", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_image_path = f"test_images/test_{timestamp}.jpg"
        cv2.imwrite(test_image_path, frame)
        print(f"✓ Test image captured and saved to {test_image_path}")
        
    except Exception as e:
        print(f"✗ Error capturing image: {str(e)}")
        return
    
    # Define objects to test for
    test_objects = ["bottle", "cup", "phone", "keyboard", "book"]
    
    # Test each object
    print("\nTesting object detection:")
    print("------------------------")
    
    for obj in test_objects:
        try:
            print(f"\nChecking for {obj}...")
            # Create a prompt
            prompt = f"Is there a {obj} in this image?"
            
            # Process the image
            start_time = time.time()
            result = process_image(frame, prompt)
            elapsed_time = time.time() - start_time
            
            # Print the result
            print(f"Gemini response ({elapsed_time:.2f}s):")
            print(f"  Found: {result['found']}")
            print(f"  Text: {result['text'][:100]}..." if len(result['text']) > 100 else f"  Text: {result['text']}")
            
        except Exception as e:
            print(f"✗ Error processing for {obj}: {str(e)}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_gemini_object_detection()
from google.generativeai import GenerativeModel
import google.generativeai as genai
from PIL import Image
import os
from dotenv import load_dotenv
import numpy as np

def setup_gemini_api():
    # Load environment variables from .env
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise Exception("GEMINI_API_KEY is not set in your .env file.")
    # Configure the API client with your key
    genai.configure(api_key=api_key)

def process_image(image, text_prompt, position=None):
    """
    Process the input image and text prompt using Gemini.
    
    Args:
        image: A PIL Image object or a NumPy array (e.g., from OpenCV or Gradio).
        text_prompt: A string containing the prompt (e.g., "Is there a bottle in this image?").
        position: Optional position ID for context/reference.
    
    Returns:
        dict: A dictionary with the following keys:
            - found (bool): Whether the object was found in the image
            - text (str): The full text response from Gemini
            - position (any): The position ID if provided
    """
    # Convert NumPy array to PIL image if necessary.
    if isinstance(image, np.ndarray):
        image = Image.fromarray(image)
    
    # Ensure the API is set up
    setup_gemini_api()
    
    try:
        # Initialize the model with the instructed model name
        model = GenerativeModel(model_name="models/gemini-2.0-flash")
        
        # Enhance the prompt to get a clear yes/no answer
        enhanced_prompt = f"""
        Analyze this image and determine if there is a {text_prompt} visible.
        Start your answer with either 'Yes' or 'No' followed by your explanation.
        """
        
        # Generate content by sending the text prompt and the image
        response = model.generate_content([enhanced_prompt, image])
        
        # Get the response text
        response_text = response.text
        
        # Parse the response to determine if the object was found
        # Look for affirmative words at the beginning of the response
        found = response_text.lower().strip().startswith(('yes', 'found', 'visible', 'i can see', 'there is'))
        
        return {
            "found": found,
            "text": response_text,
            "position": position
        }
    except Exception as e:
        print(f"Error in process_image: {str(e)}")
        # Return a safe fallback value
        return {
            "found": False,
            "text": f"Error processing image: {str(e)}",
            "position": position
        }

def generate_image_caption(image_path):
    """
    Generate a caption for an image using Gemini.
    
    Args:
        image_path (str): Path to the image file.
    
    Returns:
        str: The generated caption.
    """
    # Load the image using Pillow
    image = Image.open(image_path)
    
    # Use process_image to generate a caption with a fixed prompt
    result = process_image(image, "Describe this image in detail.")
    return result["text"]

def main():
    setup_gemini_api()
    
    # Update this path to point to your image file
    image_path = "path/to/your/image.jpg"
    
    # Generate and print the caption
    caption = generate_image_caption(image_path)
    print("Generated Caption:")
    print(caption)

if __name__ == "__main__":
    main()
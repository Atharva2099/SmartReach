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

def process_image(image, text_prompt):
    """
    Process the input image and text prompt using Gemini.
    
    Args:
        image: A PIL Image object or a NumPy array (e.g., from OpenCV or Gradio).
        text_prompt: A string containing the prompt.
    
    Returns:
        str: The generated content (text) from Gemini.
    """
    # Convert NumPy array to PIL image if necessary.
    if isinstance(image, np.ndarray):
        image = Image.fromarray(image)
    
    # Ensure the API is set up
    setup_gemini_api()
    
    # Initialize the model with the instructed model name
    model = GenerativeModel(model_name="models/gemini-2.0-flash")
    
    # Generate content by sending the text prompt and the image
    response = model.generate_content([text_prompt, image])
    
    # Return the generated text (assuming the response has a 'text' attribute)
    return response.text

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
    return process_image(image, "Describe this image in detail.")

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
from google.generativeai import GenerativeModel
import google.generativeai as genai
from PIL import Image
import os
from dotenv import load_dotenv
import numpy as np
from pydantic import BaseModel, ValidationError, validator

class GeminiDecision(BaseModel):
    decision: str

    @validator('decision')
    def must_be_yes_or_no(cls, v):
        if v.lower() not in ['yes', 'no']:
            raise ValueError('Decision must be either "yes" or "no"')
        return v.lower()

def setup_gemini_api():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise Exception("GEMINI_API_KEY is not set in your .env file.")
    genai.configure(api_key=api_key)

def process_image(image, text_prompt):
    if isinstance(image, np.ndarray):
        image = Image.fromarray(image)
    setup_gemini_api()
    model = GenerativeModel(model_name="models/gemini-2.0-flash")
    # Use a prompt that instructs a strict yes/no answer.
    refined_prompt = f"{text_prompt}\nPlease answer only yes or no."
    # Remove the temperature parameter (not supported)
    response = model.generate_content([refined_prompt, image])
    return response.text.strip()
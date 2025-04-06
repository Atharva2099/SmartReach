import gradio as gr
from utils.gemini_api import process_image

def process_and_display(image, command):
    """
    Process the image and text prompt, and display the generated content.
    
    Args:
        image: Webcam feed image (as a NumPy array)
        command: The text prompt (e.g., "is there a bottle in frame?")
    
    Returns:
        A tuple of (image, generated text) to display in the Gradio interface.
    """
    if image is None:
        return None, "No image captured."
    
    # Call our Gemini function; it now returns a string
    decision_text = process_image(image, command)
    return image, decision_text

iface = gr.Interface(
    fn=process_and_display,
    inputs=[
        gr.Image(sources=["webcam"], type="numpy", label="Webcam Feed"),
        gr.Textbox(label="Command", placeholder="e.g., is there a bottle in frame?")
    ],
    outputs=[
        gr.Image(label="Output Image"),
        gr.Textbox(label="Gemini Response")
    ],
    title="Gemini Integration with Visual Feedback",
    description="Use your webcam feed and type a command to see Gemini's generated content."
)

if __name__ == "__main__":
    iface.launch()
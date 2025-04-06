import gradio as gr
import random
import time
from utils.gemini_api import process_image
from utils.mqtt_client import start_mqtt_client, stop_mqtt_client, send_position_command, action_done_event

def wait_for_action():
    action_done_event.wait()
    action_done_event.clear()

def process_and_display(image, object_query):
    if image is None:
        return None, "No image captured."
    
    check_positions = [2, 4, 6]
    pick_map = {2: 3, 4: 5, 6: 7}
    found = False
    decision_text = ""
    
    for pos in random.sample(check_positions, len(check_positions)):
        send_position_command(pos)
        wait_for_action()
        prompt = f"Is there a {object_query} in frame? Answer yes or no."
        decision_text = process_image(image, prompt)
        if decision_text == "yes":
            send_position_command(pick_map[pos])
            wait_for_action()
            found = True
            break
    if not found:
        send_position_command(1)
        wait_for_action()
    
    return image, decision_text

iface = gr.Interface(
    fn=process_and_display,
    inputs=[
        gr.Image(sources=["webcam"], type="numpy", label="Webcam Feed"),
        gr.Textbox(label="Object Query", placeholder="Enter object, e.g., bottle")
    ],
    outputs=[
        gr.Image(label="Output Image"),
        gr.Textbox(label="Gemini Decision")
    ],
    title="SmartReach Gemini Integration",
    description="Live webcam feed with Gemini decision processing and MQTT command publishing."
)

if __name__ == "__main__":
    start_mqtt_client()
    iface.launch()
    stop_mqtt_client()
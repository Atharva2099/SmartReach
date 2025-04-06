import gradio as gr
import sys
import json
from utils.gemini_api import process_image
from utils.mqtt_client import start_mqtt_client, stop_mqtt_client, client, set_broker_address

def process_and_display(image, command, broker_ip):
    """
    Process the input image and command with Gemini integration.
    Also handles robot control commands via MQTT if applicable.
    
    Args:
        image: Webcam feed image (as a NumPy array)
        command: The text prompt (e.g., "is there a bottle in frame?")
        broker_ip: IP address of the MQTT broker
    
    Returns:
        A tuple of (image, generated text) to display in the Gradio interface.
    """
    if image is None:
        return None, "No image captured."
    
    # Check if we need to update the broker IP
    if broker_ip:
        set_broker_address(broker_ip)
        client.disconnect()
        start_mqtt_client()
    
    # Parse for robot control commands
    if command.lower().startswith(("move to", "go to")):
        try:
            # Extract position number
            position = command.split()[-1]
            pos_key = int(position)
            
            # Call the Gemini API to analyze the image
            gemini_response = process_image(image, f"Describe what you see in this image.")
            
            # Send robot control command via MQTT
            client.publish("smartreach/command", json.dumps({
                "command": "move_to_position",
                "position_key": pos_key
            }))
            
            response = f"Sent command to move to position {pos_key}.\n\nGemini's analysis: {gemini_response}"
            return image, response
            
        except ValueError:
            # If position is not a valid number
            return image, f"Invalid position number. Please specify a valid position number."
    
    # For non-robot commands, just process with Gemini
    gemini_response = process_image(image, command)
    return image, gemini_response

def main():
    # Parse command line arguments for broker IP
    default_broker_ip = "192.168.1.100"
    if len(sys.argv) > 1:
        default_broker_ip = sys.argv[1]
    
    # Start MQTT client
    set_broker_address(default_broker_ip)
    start_mqtt_client()
    
    # Create the Gradio Interface
    iface = gr.Interface(
        fn=process_and_display,
        inputs=[
            gr.Image(sources=["webcam"], type="numpy", label="Webcam Feed"),
            gr.Textbox(label="Command", placeholder="e.g., is there a bottle in frame?"),
            gr.Textbox(label="MQTT Broker IP", placeholder="IP address of Linux machine", value=default_broker_ip)
        ],
        outputs=[
            gr.Image(label="Output Image"),
            gr.Textbox(label="Response")
        ],
        title="SmartReach: Gemini + Robot Control",
        description="Use your webcam feed and type a command to control the robot and see Gemini's analysis."
    )
    
    # Launch the interface
    try:
        iface.launch()
    finally:
        # Clean up MQTT client on exit
        stop_mqtt_client()
        print("Gradio app shutdown complete")

if __name__ == "__main__":
    main()
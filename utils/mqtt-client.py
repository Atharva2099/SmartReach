import paho.mqtt.client as mqtt
import time
import json
import queue
import threading

# Create a queue for receiving status messages from the robot
status_queue = queue.Queue()

# MQTT settings - update this to your Linux machine's IP
MQTT_BROKER = "192.168.1.100"  # Change to your teammate's Linux IP
MQTT_PORT = 1883
TOPIC_COMMAND = "smartreach/command"
TOPIC_STATUS = "smartreach/status"

# Configure MQTT client
client = mqtt.Client()

# Define callbacks
def on_connect(client, userdata, flags, rc):
    """Callback for when the client connects to the broker."""
    print(f"Connected to MQTT broker with result code {rc}")
    # Subscribe to status updates from the robot
    client.subscribe(TOPIC_STATUS)
    # Publish that we're online
    client.publish(TOPIC_COMMAND, json.dumps({"command": "status_check"}))

def on_disconnect(client, userdata, rc):
    """Callback for when the client disconnects from the broker."""
    if rc != 0:
        print(f"Unexpected disconnection. Will auto-reconnect. Code: {rc}")
    else:
        print("Disconnected from MQTT broker")

def on_message(client, userdata, msg):
    """Callback for when a message is received from the broker."""
    try:
        data = json.loads(msg.payload.decode())
        print(f"Status update: {data}")
        # Put the status message in the queue for processing by the main thread
        status_queue.put(data)
    except Exception as e:
        print(f"Error processing message: {e}")

# Function to replace your current go_to_position
def go_to_position(pos_key):
    """
    Send command to move robot to specified position.
    Returns True if successful, False otherwise.
    """
    print(f"Requesting move to position {pos_key}")
    client.publish(TOPIC_COMMAND, json.dumps({
        "command": "move_to_position",
        "position_key": pos_key
    }))
    
    # Wait for confirmation (optional)
    try:
        status = status_queue.get(timeout=10.0)  # Wait up to 10 seconds for a response
        if status.get("status") == "success":
            print(f"Successfully moved to position {pos_key}")
            return True
        else:
            print(f"Error moving to position: {status.get('message', 'Unknown error')}")
            return False
    except queue.Empty:
        print("Timed out waiting for position confirmation")
        return False

def start_mqtt_client():
    """Start the MQTT client and connect to the broker."""
    # Set up callbacks
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    
    # Connect to broker
    print(f"Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
    
    # Set up automatic reconnection
    client.reconnect_delay_set(min_delay=1, max_delay=120)
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        # Start the loop in a separate thread
        client.loop_start()
        return True
    except Exception as e:
        print(f"Failed to connect to MQTT broker: {e}")
        return False

def stop_mqtt_client():
    """Stop the MQTT client and disconnect from the broker."""
    try:
        client.publish(TOPIC_COMMAND, json.dumps({"command": "client_disconnecting"}))
        time.sleep(0.5)  # Give a moment for the message to be sent
        client.loop_stop()
        client.disconnect()
        print("MQTT client stopped and disconnected")
    except Exception as e:
        print(f"Error stopping MQTT client: {e}")
        
def set_broker_address(broker_ip):
    """Update the broker address (useful for configuration at runtime)."""
    global MQTT_BROKER
    MQTT_BROKER = broker_ip
    print(f"MQTT broker address updated to {MQTT_BROKER}")
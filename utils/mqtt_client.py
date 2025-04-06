import paho.mqtt.client as mqtt
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MQTT_BROKER = "10.0.0.42"  # Updated to the Linux machine's IP address
MQTT_PORT = 1883
TOPIC_COMMAND = "smartreach/command"

client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    logger.info(f"Connected to MQTT broker with result code {rc}")

def on_disconnect(client, userdata, rc):
    if rc != 0:
        logger.warning(f"Unexpected disconnection with code {rc}")
    else:
        logger.info("Disconnected from MQTT broker")

def start_mqtt_client():
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    logger.info(f"Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()

def stop_mqtt_client():
    client.loop_stop()
    client.disconnect()

def send_position_command(position_key):
    payload = {
        "command": "move_to_position",
        "position_key": position_key
    }
    message = json.dumps(payload)
    logger.info(f"Publishing message: {message}")
    client.publish(TOPIC_COMMAND, message)
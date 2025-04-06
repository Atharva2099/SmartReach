# File: mqtt_test.py
from utils.mqtt_client import start_mqtt_client, send_position_command, stop_mqtt_client
import time

def main():
    start_mqtt_client()
    send_position_command(2)
    time.sleep(1)
    send_position_command(3)
    time.sleep(1)
    send_position_command(1)
    stop_mqtt_client()

if __name__ == "__main__":
    main()
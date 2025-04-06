import time
from utils.mqtt_client import start_mqtt_client, stop_mqtt_client, client, set_broker_address
import json
import sys

def main():
    # Allow setting the broker IP from command line
    if len(sys.argv) > 1:
        broker_ip = sys.argv[1]
        set_broker_address(broker_ip)
        print(f"Using broker address: {broker_ip}")
    
    # Start MQTT client
    if not start_mqtt_client():
        print("Failed to start MQTT client. Exiting.")
        return
    
    # Send a test message
    print("Sending test message...")
    client.publish("smartreach/command", json.dumps({
        "command": "test_connection",
        "timestamp": time.time()
    }))
    
    print("Waiting for response (10 seconds)...")
    try:
        # Keep the script running for a bit to receive responses
        for i in range(10):
            print(f"Waiting... {10-i} seconds remaining")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    finally:
        stop_mqtt_client()
        print("Test completed")

if __name__ == "__main__":
    main()
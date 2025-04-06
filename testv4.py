import json
import time
import sys
import tty
import termios
import select
import paho.mqtt.client as mqtt
from threading import Thread
from lerobot.common.robot_devices.motors.configs import FeetechMotorsBusConfig
from lerobot.common.robot_devices.motors.feetech import FeetechMotorsBus

##sudo chmod 666 /dev/ttyACM1
## ls /dev/ttyACM*


# Port configuration
PORT = "/dev/ttyACM0"
MOTOR_IDS = [1, 2, 3, 4, 5, 6]
MOTOR_MODEL = "sts3215"
MOTOR_MODELS = [MOTOR_MODEL] * len(MOTOR_IDS)
BAUDRATE = 1_000_000

# Lower acceleration for smoother movement
PID_P, PID_I, PID_D = 5, 1, 0
ACCELERATION = 15

# JSON file with saved positions
JSON_FILE = "robot_sequences.json"

# MQTT Settings
MQTT_BROKER = "localhost"  # Change this to your MQTT broker address
MQTT_PORT = 1883
MQTT_COMMAND_TOPIC = "smartreach/command"
MQTT_STATUS_TOPIC = "smartreach/status"  # New topic for status updates


def load_position_sequences():
    """Load position sequences from JSON file"""
    try:
        with open(JSON_FILE, 'r') as file:
            sequences = json.load(file)
        print(f"Successfully loaded {len(sequences)} sequences from {JSON_FILE}")
        return sequences
    except Exception as e:
        print(f"Error loading sequences from {JSON_FILE}: {e}")
        return []


def get_sequence_by_key(sequences, key):
    """Get a sequence by its key from the JSON data"""
    for sequence in sequences:
        if sequence["key"] == key:
            return sequence["positions"]
    return None


def set_torque(motor_bus, enable=False):
    """Enable or disable torque for all motors"""
    value = 1 if enable else 0
    motor_bus.write_with_motor_ids(
        motor_models=MOTOR_MODELS,
        motor_ids=MOTOR_IDS,
        data_name="Torque_Enable",
        values=[value] * len(MOTOR_IDS),
    )


def set_goal(motor_bus, position):
    """Set goal position for all motors"""
    motor_bus.write_with_motor_ids(
        motor_models=MOTOR_MODELS,
        motor_ids=MOTOR_IDS,
        data_name="Goal_Position",
        values=position,
    )


def get_current_positions(motor_bus):
    """Get current positions of all motors"""
    current_positions = []
    for motor_id in MOTOR_IDS:
        current_position = motor_bus.read_with_motor_ids(
            motor_models=[MOTOR_MODEL],
            motor_ids=[motor_id],
            data_name="Present_Position",
        )[0]
        current_positions.append(current_position)
    return current_positions


def move_to_position(motor_bus, position, steps=20, delay=0.1):
    """Move to position with interpolation for smooth movement"""
    # Get current position
    current_positions = get_current_positions(motor_bus)
    
    # Create and execute smooth path to target position
    path = interpolate_positions(current_positions, position, steps=steps)
    for pos in path:
        set_goal(motor_bus, pos)
        time.sleep(delay)


def interpolate_positions(start_pos, end_pos, steps=20):
    """Create intermediate positions between start and end for smooth movement"""
    result = []
    for step in range(steps + 1):
        fraction = step / steps
        interpolated_pos = []
        for i in range(len(start_pos)):
            value = start_pos[i] + (end_pos[i] - start_pos[i]) * fraction
            interpolated_pos.append(int(value))
        result.append(interpolated_pos)
    return result


def execute_sequence(motor_bus, positions, steps=15, delay=0.05, pause=0.5, mqtt_client=None, sequence_key=None):
    """Execute a sequence of positions with smooth transitions and send status updates"""
    for i, position in enumerate(positions):
        move_to_position(motor_bus, position, steps=steps, delay=delay)
        
        # Send progress update if MQTT client is provided
        if mqtt_client and sequence_key is not None:
            progress = {
                "status": "in_progress",
                "position_key": sequence_key,
                "position_index": i,
                "total_positions": len(positions),
                "timestamp": time.time()
            }
            mqtt_client.publish(MQTT_STATUS_TOPIC, json.dumps(progress))
            print(f"Published progress: {progress}")
            
        time.sleep(pause)  # Pause at each position
    
    # Send completion status if MQTT client is provided
    if mqtt_client and sequence_key is not None:
        completion = {
            "status": "completed",
            "position_key": sequence_key,
            "timestamp": time.time()
        }
        mqtt_client.publish(MQTT_STATUS_TOPIC, json.dumps(completion))
        print(f"Published completion: {completion}")


def getch():
    """Get a single character from standard input"""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


def kbhit():
    """Check if a keypress is available"""
    dr, dw, de = select.select([sys.stdin], [], [], 0)
    return dr != []


def on_connect(client, userdata, flags, rc):
    """Callback for when the client connects to the MQTT broker"""
    print(f"Connected to MQTT broker with result code {rc}")
    client.subscribe(MQTT_COMMAND_TOPIC)
    print(f"Subscribed to topic: {MQTT_COMMAND_TOPIC}")


def on_message(client, userdata, msg):
    """Callback for when a message is received from the MQTT broker"""
    try:
        # Decode and parse the JSON message
        payload = msg.payload.decode('utf-8')
        print(f"Received MQTT message: {payload}")
        
        data = json.loads(payload)
        
        # Check if the message has the expected format
        if "command" in data and data["command"] == "move_to_position" and "position_key" in data:
            position_key = data["position_key"]
            print(f"Received command to move to position key: {position_key}")
            
            # Send acknowledgment that command was received
            ack = {
                "status": "received",
                "position_key": position_key,
                "timestamp": time.time()
            }
            client.publish(MQTT_STATUS_TOPIC, json.dumps(ack))
            print(f"Published acknowledgment: {ack}")
            
            # Process the command
            process_command(position_key, userdata['motor_bus'], userdata['sequences'], client)
        else:
            print(f"Invalid MQTT message format: {payload}")
    except json.JSONDecodeError:
        print(f"Error decoding JSON message: {payload}")
    except Exception as e:
        print(f"Error processing MQTT message: {e}")
        # Send error status
        try:
            error_status = {
                "status": "error",
                "error_message": str(e),
                "timestamp": time.time()
            }
            client.publish(MQTT_STATUS_TOPIC, json.dumps(error_status))
        except:
            pass


def setup_mqtt_client(motor_bus, sequences):
    """Setup and start the MQTT client"""
    client = mqtt.Client()
    
    # Store motor_bus and sequences in userdata for use in callbacks
    client.user_data_set({
        'motor_bus': motor_bus,
        'sequences': sequences
    })
    
    # Set up callbacks
    client.on_connect = on_connect
    client.on_message = on_message
    
    # Connect to broker
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        
        # Start MQTT loop in a background thread
        client.loop_start()
        print(f"MQTT client started and connected to {MQTT_BROKER}:{MQTT_PORT}")
        return client
    except Exception as e:
        print(f"Failed to connect to MQTT broker: {e}")
        return None


def process_command(key_num, motor_bus, sequences, mqtt_client=None):
    """Process a command to execute a sequence for the given key"""
    try:
        key_num = int(key_num)
        sequence_positions = get_sequence_by_key(sequences, key_num)
        
        if sequence_positions:
            print(f"Executing sequence {key_num} with {len(sequence_positions)} positions...")
            
            # Send started status
            if mqtt_client:
                started = {
                    "status": "started",
                    "position_key": key_num,
                    "timestamp": time.time()
                }
                mqtt_client.publish(MQTT_STATUS_TOPIC, json.dumps(started))
                print(f"Published started: {started}")
            
            # Execute the sequence with MQTT client for status updates
            execute_sequence(motor_bus, sequence_positions, mqtt_client=mqtt_client, sequence_key=key_num)
        else:
            print(f"No sequence found for key {key_num}")
            # Send not found status
            if mqtt_client:
                not_found = {
                    "status": "error",
                    "error_message": f"No sequence found for key {key_num}",
                    "timestamp": time.time()
                }
                mqtt_client.publish(MQTT_STATUS_TOPIC, json.dumps(not_found))
    except ValueError:
        print(f"Invalid key number: {key_num}")
        # Send error status
        if mqtt_client:
            error_status = {
                "status": "error",
                "error_message": f"Invalid key number: {key_num}",
                "timestamp": time.time()
            }
            mqtt_client.publish(MQTT_STATUS_TOPIC, json.dumps(error_status))


def keyboard_input_thread(motor_bus, sequences, running, mqtt_client):
    """Thread function to handle keyboard input"""
    print("Keyboard input thread started")
    print("Press keys 0-9 to execute sequences, 'q' to exit.")
    
    while running['value']:
        # Wait for key press using standard input
        key = getch()
        
        if key in '0123456789':
            key_num = int(key)
            process_command(key_num, motor_bus, sequences, mqtt_client)
        elif key in ['q', 'Q', '\x1b']:  # q, Q or ESC
            print("Exiting...")
            running['value'] = False


def main():
    # Load sequences from JSON file
    sequences = load_position_sequences()
    if not sequences:
        print("Failed to load position sequences. Exiting.")
        return

    # Initialize the motor bus
    config = FeetechMotorsBusConfig(
        port=PORT,
        motors={"motor": (-1, MOTOR_MODEL)},
    )
    motor_bus = FeetechMotorsBus(config)
    motor_bus.connect()
    
    print("Robot arm control initialized.")
    
    try:
        # Disable torque to configure motors
        set_torque(motor_bus, enable=False)
        
        # Configure motors for smooth movement
        for field, value in (
            ("Mode", 0),
            ("P_Coefficient", PID_P),
            ("I_Coefficient", PID_I),
            ("D_Coefficient", PID_D),
            ("Maximum_Acceleration", ACCELERATION),
            ("Acceleration", ACCELERATION),
        ):
            motor_bus.write_with_motor_ids(
                motor_models=MOTOR_MODELS,
                motor_ids=MOTOR_IDS,
                data_name=field,
                values=[value] * len(MOTOR_IDS),
            )
        
        # Enable torque
        set_torque(motor_bus, enable=True)
        
        # Set up MQTT client
        mqtt_client = setup_mqtt_client(motor_bus, sequences)
        
        # Start at home position (using sequence 0's first position)
        home_sequence = get_sequence_by_key(sequences, 0)
        if home_sequence and len(home_sequence) > 0:
            print("Moving to home position...")
            move_to_position(motor_bus, home_sequence[0])
            
            # Send home position status
            if mqtt_client:
                home_status = {
                    "status": "initialized",
                    "position": "home",
                    "timestamp": time.time()
                }
                mqtt_client.publish(MQTT_STATUS_TOPIC, json.dumps(home_status))
        
        # Use a dict with a 'value' key for the running flag so it can be modified by reference
        running = {'value': True}
        
        # Start keyboard input thread
        kb_thread = Thread(target=keyboard_input_thread, args=(motor_bus, sequences, running, mqtt_client))
        kb_thread.daemon = True
        kb_thread.start()
        
        # Main thread just waits until running becomes False
        while running['value']:
            time.sleep(0.1)
                
    finally:
        # Ensure we cleanup before exit
        print("Shutting down...")
        
        # Send shutdown status
        if 'mqtt_client' in locals() and mqtt_client is not None:
            shutdown_status = {
                "status": "shutdown",
                "timestamp": time.time()
            }
            mqtt_client.publish(MQTT_STATUS_TOPIC, json.dumps(shutdown_status))
            
            # Stop MQTT client
            mqtt_client.loop_stop()
            mqtt_client.disconnect()
            print("MQTT client disconnected")
        
        set_torque(motor_bus, enable=False)
        motor_bus.disconnect()
        print("Motor bus disconnected")


if __name__ == "__main__":
    main()

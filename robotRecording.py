import json
import os
import sys
import time
import tty
import termios
import select

# === Dummy Classes for Testing (replace these with actual imports if available) ===
class FeetechMotorsBusConfig:
    def __init__(self, port, motors):
        self.port = port
        self.motors = motors

class FeetechMotorsBus:
    def __init__(self, config):
        self.config = config
    def connect(self):
        print(f"Dummy motor bus connected on port {self.config.port}")
    def disconnect(self):
        print("Dummy motor bus disconnected")
    def read_with_motor_ids(self, motor_models, motor_ids, data_name):
        # Return dummy motor positions for testing.
        return [1000 for _ in motor_ids]

# If you eventually have the real module, comment out the dummy classes above
# and uncomment the following lines:
# from lerobot.common.robot_devices.motors.configs import FeetechMotorsBusConfig
# from lerobot.common.robot_devices.motors.feetech import FeetechMotorsBus

# === Global Configuration ===
PORT = "/dev/ttyACM0"
MOTOR_IDS = [1, 2, 3, 4, 5, 6]
MOTOR_MODEL = "sts3215"
MOTOR_MODELS = [MOTOR_MODEL] * len(MOTOR_IDS)
BAUDRATE = 1_000_000
JSON_FILE = "robot_sequences.json"

# === Helper Functions ===

def getch():
    """Get a single character from standard input."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

def kbhit():
    """Check if a keypress is available."""
    dr, dw, de = select.select([sys.stdin], [], [], 0)
    return dr != []

def get_position(motor_bus):
    """Get current positions of all motors."""
    return motor_bus.read_with_motor_ids(
        motor_models=MOTOR_MODELS,
        motor_ids=MOTOR_IDS,
        data_name="Present_Position",
    )

def load_sequences():
    """Load existing sequences from JSON file in array format."""
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, 'r') as file:
                sequences = json.load(file)
                # Convert to array format if it's not already
                if isinstance(sequences, dict):
                    array_sequences = []
                    for key, positions in sequences.items():
                        array_sequences.append({
                            "key": int(key),
                            "positions": positions
                        })
                    return array_sequences
                return sequences
        except json.JSONDecodeError:
            print(f"Error reading {JSON_FILE}. Creating a new file.")
            return []
    return []

def save_sequences(sequences):
    """Save sequences to JSON file in array format."""
    with open(JSON_FILE, 'w') as file:
        json.dump(sequences, file, indent=4)
    print(f"Sequences saved to {JSON_FILE}")

def find_sequence_by_key(sequences, key):
    """Find a sequence with the given key."""
    for i, sequence in enumerate(sequences):
        if sequence["key"] == key:
            return i
    return -1

def record_sequence(motor_bus):
    """Record a sequence of robot positions."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    
    try:
        # Restore normal terminal settings for input
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        while True:
            try:
                sequence_key = int(input("Enter a number for this sequence: "))
                break
            except ValueError:
                print("Please enter a valid number.")
    finally:
        # Set terminal to raw mode for getch
        tty.setraw(fd)
    
    # Reset terminal settings
    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    
    positions = []
    
    print("\n--- RECORDING MODE ---")
    print("Press 'a' to record current position")
    print("Press 's' to save the sequence")
    print("Press 'q' to quit without saving")
    print("Current position values will update continuously below:")
    
    recording = True
    try:
        tty.setraw(fd)
        while recording:
            current_position = get_position(motor_bus)
            position_str = ', '.join([f"{pos:4d}" for pos in current_position])
            
            sys.stdout.write("\r" + " " * 80)  # Clear the line
            sys.stdout.write(f"\rCurrent position: [{position_str}]")
            sys.stdout.flush()
            
            if kbhit():
                key = sys.stdin.read(1)
                if key == 'a':
                    positions.append(current_position)
                    sys.stdout.write("\n" + " " * 80)
                    sys.stdout.write(f"\nPosition {len(positions)} recorded: {current_position}\n")
                    sys.stdout.flush()
                elif key == 's':
                    if positions:
                        recording = False
                        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                        print("\nSaving sequence...")
                        return sequence_key, positions
                    else:
                        sys.stdout.write("\n" + " " * 80)
                        sys.stdout.write("\nNo positions recorded, nothing to save.\n")
                        sys.stdout.flush()
                elif key == 'q':
                    recording = False
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                    print("\nExiting without saving...")
                    return None, None
            time.sleep(0.1)
    except Exception as e:
        print(f"\nError during recording: {e}")
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return None, None

# === Primary Functionality ===

def execute_positions(step):
    """
    Execute a given robot step.
    This function sends a single robot step command to the motors.
    """
    print(f"Executing step: {step}")
    # Insert your actual robot control code here.

def main():
    print("Robot Position Recorder")
    print("=======================")
    
    sequences = load_sequences()
    print(f"Loaded {len(sequences)} existing sequences")
    
    config = FeetechMotorsBusConfig(
        port=PORT,
        motors={"motor": (-1, MOTOR_MODEL)},
    )
    motor_bus = FeetechMotorsBus(config)
    motor_bus.connect()
    print("Connected to motor bus")
    
    try:
        while True:
            sequence_key, positions = record_sequence(motor_bus)
            
            if sequence_key is not None and positions:
                sequence_index = find_sequence_by_key(sequences, sequence_key)
                if sequence_index >= 0:
                    sequences[sequence_index]["positions"] = positions
                    print(f"Updated sequence {sequence_key} with {len(positions)} positions")
                else:
                    sequences.append({
                        "key": sequence_key,
                        "positions": positions
                    })
                    print(f"Added new sequence {sequence_key} with {len(positions)} positions")
                sequences.sort(key=lambda x: x["key"])
                save_sequences(sequences)
                print(f"Sequence {sequence_key} saved successfully")
            
            choice = input("Record another sequence? (y/n): ")
            if choice.lower() != 'y':
                break
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        motor_bus.disconnect()
        print("Motor bus disconnected")

if __name__ == "__main__":
    main()
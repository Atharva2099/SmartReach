# SmartReach

SmartReach is an advanced robotics control project that integrates a state-machine-based robot controller with Google's Gemini generative AI and a Gradio interface for live visual feedback. The project is designed to enable complex robotic tasks—such as object detection, picking, and moving—by combining robotics control, image analysis, and natural language processing in a modular, extensible codebase.

---

## Project Overview

SmartReach leverages several core components:

- **Robot Control & State Machine:**  
  The core control system uses predefined position sequences to command a robot through different states (e.g., Home, Active, Check, Pick, Show, Drop). These sequences are stored in `robot_sequences.json` and are used by the main controller (`main.py`) to determine which actions to perform next.

- **Gemini Integration:**  
  The project uses Google’s Gemini generative AI to analyze images captured by the robot’s camera. The Gemini integration, implemented in `utils/gemini_api.py`, uses the native multimodal model `"models/gemini-2.0-flash"` to process both text prompts and images. This integration is used for tasks such as generating image captions or verifying object presence.

- **Gradio Interface:**  
  The Gradio interface (`gradio_app.py`) provides a web-based UI to display a live webcam feed and accept text commands. This interface facilitates interactive testing and debugging by showing Gemini's output in real time.

- **Configuration and Environment Management:**  
  Sensitive data such as the Gemini API key is stored in a `.env` file (which is ignored by Git) and loaded into the application using the `python-dotenv` package.

---

## Detailed Workflow

### State Machine Workflow

```markdown
[0] HOME  
  └── On start, transition to [1] ACTIVE

[1] ACTIVE  
  ├── On "check position X": move only to that specific check state (2, 4, or 6)  
  ├── On "find object": choose a random check position (2, 4, or 6) and, in search mode, explore unvisited positions until the object is found  
  ├── On "show me": transition to [8] to show the object to the human  
  ├── On "drop it" (when a hand is visible): transition to [9] to drop the object  
  └── On "go home" or shutdown: return to [0] HOME

[2/4/6] Check Position (capture image + Gemini image analysis)  
  ├── If the object is found → transition to corresponding Pick state ([3], [5], or [7])  
  └── If the object is not found →  
      - In search mode: continue exploring the next unvisited check position  
      - In direct mode: return to [1] ACTIVE

[3/5/7] Pick + Return to ACTIVE  
  (Execute the pick operation at the current check position, then return to [1] ACTIVE)

[8] Show to Human  
  (Move from ACTIVE to a position where the object is shown to a human)

[9] Drop at Human  
  (Drop the object when a human hand is detected)

How the Workflow Functions
	•	Initialization & Setup:
The system initializes by configuring the Gemini API with your API key (from .env), and setting up dependencies and position data.
	•	Robot Control:
The state machine, implemented in main.py, drives the robot through various positions (e.g., from Active to Check states). Depending on the command (e.g., “find object” or “check position X”), the robot moves accordingly.
	•	Image Analysis:
At check positions (keys 2, 4, 6), the robot captures an image and calls the Gemini API (via utils/gemini_api.py) to analyze the scene. Based on the response (object found or not), the state machine transitions to the corresponding Pick state (keys 3, 5, 7) or continues searching.
	•	User Interaction via Gradio:
The Gradio interface (gradio_app.py) displays a live webcam feed and accepts text commands. When a command is entered (for example, “is there a bottle in frame?”), it invokes the Gemini integration and displays the generated response, facilitating real-time interaction and debugging.
	•	Version Control & Security:
The repository is managed using Git. Sensitive files (e.g., .env) and system files (e.g., __pycache__, .DS_Store) are excluded via .gitignore. The branch is renamed from master to main before pushing to ensure compliance with modern Git practices.

⸻

Setup and Running the Project

Prerequisites
	•	Python 3.8 or higher
	•	Git installed on your system
	•	A valid Gemini API key stored in a .env file

Installation Steps
	1.	Clone the Repository:

git clone https://github.com/Atharva2099/SmartReach.git
cd SmartReach


	2.	Set Up a Virtual Environment:

python3 -m venv so100arm
source so100arm/bin/activate


	3.	Install Dependencies:

pip install -r requirements.txt


	4.	Configure Environment Variables:
	•	Create a .env file in the project root with the following content:

GEMINI_API_KEY=your_actual_api_key_here


	•	Ensure that .env is listed in your .gitignore.

	5.	Run the Gradio App for Testing:

python gradio_app.py

This launches a local server (typically at http://127.0.0.1:7860) where you can view the live webcam feed and enter text commands.

	6.	Test the Robot Control:
	•	Use main.py to run the state machine controlling robot movements and image capture for Gemini analysis.

⸻

File Structure

so100_controller_project/
├── .env                # Environment variables (ignored by Git)
├── .gitignore          # Git ignore file to exclude sensitive/system files
├── README.md           # Detailed project description and workflow
├── requirements.txt    # List of required Python packages
├── main.py             # Entry point for the robot state machine and control logic
├── gradio_app.py       # Gradio interface for live webcam feed and Gemini interaction
├── robot_sequences.json# JSON file containing robot movement sequences
├── robotRecording.py   # Script for recording and executing robot positions
├── IK.py               # Inverse kinematics related code
└── utils/
    └── gemini_api.py   # Gemini API integration and image processing logic



⸻

License

This project is licensed under the MIT License.

⸻

Future Enhancements
	•	Voice Interface: Integrate a voice recognition system for real-time command input.
	•	Enhanced Gemini API Integration: Improve image handling by using native file uploads once supported by the Gemini API.
	•	Improved State Machine: Enhance the robot’s decision-making process and error handling.
	•	Additional Visual Feedback: Extend the Gradio interface with more detailed debugging and logging information.

⸻



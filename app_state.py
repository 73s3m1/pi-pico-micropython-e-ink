"""
    MicroPython Application Management
    
    This script provides methods for managing the state of an application in a MicroPython environment.
    
    It includes the following features:
    
    1. Checking for file existence and type.
    2. Clearing and saving the application state to a JSON file.
    3. Loading the state from a JSON file.
    4. Updating the state with application-related information.
    5. Dynamically importing and launching application modules.
    
    Global Variables:
    - state: Stores the state of the application, initialized with {"run": None}.
    - app: Reference to the currently loaded application module.
    
    Functions:
    - file_exists(filename): Checks if a given file exists and is a regular file.
    - clear_state(): Deletes the state file if it exists.
    - save_state(data): Saves the given state data to a JSON file.
    - load_state(): Loads state data from the JSON file into the global state variable.
    - update_state(running): Updates the state with a new running status and saves it.
    - launch_app(app_name): Imports an application module by name and updates the state, with error handling.
"""

import time
import os
import json

# Global variable that stores the state of the application.
state = {"run": None}

# Global reference to the currently loaded application module.
app = None

# Define day and night time intervals (24 h time interval).
DAY_START = 8
DAY_END = 23

def get_app_update_interval(day_update_interval, night_update_interval):
    """
    Determines the appropriate update interval based on the current time.
    
    This function checks the current hour of the day and compares it against the
    provided day start and end times. If the current time falls within the
    defined daytime interval, it returns the specified daytime update interval.
    Otherwise, it returns the nighttime update interval.
    
    Args:
        day_update_interval (int): The update interval (in minutes) to be used during the daytime.
        night_update_interval (int): The update interval (in minutes) to be used during the nighttime.
    
    Returns:
        int: The update interval (in minutes) based on the current time.
    """
    current_time = time.localtime()
    current_hour = current_time[3]
    
    if DAY_START <= current_hour < DAY_END:
        return day_update_interval
    else:
        return night_update_interval

def state_file_exists(filename):
    """
    Checks if a file exists and is a regular file (not a directory).
    
    :param filename: The path to the file to check.
    :return: True if the file exists and is a regular file, False otherwise.
    """
    try:
        return os.stat(filename)[0] & 0x8000  # Check for regular file (0x8000 indicates a regular file)
    except OSError:
        return False

def clear_state():
    """
    Deletes the state file if it exists.
    """
    if state_file_exists("/state.json"):
        os.remove("/state.json")

def save_state(data):
    """
    Saves the given state data to a JSON file.
    
    :param data: The state data to save, expected to be a dictionary.
    """
    with open("/state.json", "w") as f:
        f.write(json.dumps(data)) 

def load_state():
    """
    Loads the state data from the JSON file into the global state variable.
    If the file cannot be read or the data is invalid, initializes state with default values.
    """
    global state
    try:
        with open("/state.json", "r") as f:
            data = json.loads(f.read())
        if isinstance(data, dict):
            state = data
    except OSError:
        state = {"run": None}

def update_state(running):
    """
    Updates the state with the given running status and saves it.
    
    :param running: The new running status to store in the state.
    """
    global state
    state['run'] = running
    save_state(state)

def launch_app(app_name):
    """
    Dynamically imports an application module and updates the state with the application name.
    
    :param app_name: The name of the application module to import.
    """
    global app
    try:
        # Import the application module.
        app = __import__(app_name)
        
        # Print the imported module for debugging.
        print(app)
        
        # Update state with the application name.
        update_state(app_name)
    except ImportError as e:
        # Print an error message if the import fails.
        print(f"Error importing app: {e}")
        
        # Set app to None in case of an import error.
        app = None
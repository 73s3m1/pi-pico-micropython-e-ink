"""
    This script is the main driver of this microcontroller.
    
    The main script provides a launcher application to start different apps.
    
    For some of these apps an SD card or WIFI is required.
"""

import jpegdec
import gc
import time
import network_util as ih
import app_state as sh

from machine import reset

# For importing PicoGraphics we need to specify the size of the Inky Frame (in this case 5.7").
from picographics import PicoGraphics, DISPLAY_INKY_FRAME as DISPLAY

# Next we need a short delay to give USB a chance to initialise.
time.sleep(0.5)

# Then we are ready to import the PicoGraphics.
graphics = PicoGraphics(DISPLAY)

# Retrive width and height bounds from display for later use.
WIDTH, HEIGHT = graphics.get_bounds()

# Turn any LEDs off that may still be on from last run.
ih.clear_button_leds()
ih.led_warn.off()

# Define all available colors for the e-ink screen.
BLACK = 0
WHITE = 1
GREEN = 2
BLUE = 3
RED = 4
YELLOW = 5
ORANGE = 6
TAUPE = 7

def draw_option(text, x, y, width, height, text_size):
    """
    Draws a single option on the launcher menu.

    Parameters:
    - text (str): The label of the menu option.
    - x (int): The x-coordinate of the top-left corner of the option box.
    - y (int): The y-coordinate of the top-left corner of the option box.
    - width (int): The width of the option box.
    - height (int): The height of the option box.
    - text_size (int): The size of the text to be drawn.

    Returns:
    - None
    """
    global graphics
    
    graphics.set_pen(ORANGE)
    graphics.rectangle(x, y, width, height)
    graphics.set_pen(WHITE)
    graphics.text(text, x + 5, y + 15, width, text_size)

def draw_highlight(x, y, width, height):
    """
    Draws a highlight box behind the menu option.

    Parameters:
    - x (int): The x-coordinate of the top-left corner of the highlight box.
    - y (int): The y-coordinate of the top-left corner of the highlight box.
    - width (int): The width of the highlight box.
    - height (int): The height of the highlight box.

    Returns:
    - None
    """
    global graphics
    
    graphics.set_pen(graphics.create_pen(220, 220, 220))
    graphics.rectangle(x, y, width, height)

def draw_launcher_menu():
    """
    Draws the complete launcher menu on the screen, including title, options, and highlights.

    Parameters:
    - None

    Returns:
    - None
    """
    global graphics
    
    y_offset = 20
    
    graphics.set_pen(WHITE)
    graphics.clear()
    graphics.set_pen(ORANGE)
    graphics.rectangle(0, 0, WIDTH, 50)
    graphics.set_pen(WHITE)
    
    title = "Launcher"
    title_len = graphics.measure_text(title, 4) // 2
    graphics.text(title, (WIDTH // 2 - title_len), 10, WIDTH, 4)
    
    options = [
        ("A. Nasa Picture", 30, HEIGHT - (340 + y_offset), WIDTH - 100, 50, 3),
        ("B. Pictures", 30, HEIGHT - (280 + y_offset), WIDTH - 150, 50, 3),
        ("C. Weather", 30, HEIGHT - (220 + y_offset), WIDTH - 200, 50, 3),
        ("D. Headlines", 30, HEIGHT - (160 + y_offset), WIDTH - 250, 50, 3),
        ("E. -XKCD", 30, HEIGHT - (100 + y_offset), WIDTH - 300, 50, 3),
    ]
    
    for option in options:
        draw_option(*option)
    
    highlights = [
        (WIDTH - 100, HEIGHT - (340 + y_offset), 70, 50),
        (WIDTH - 150, HEIGHT - (280 + y_offset), 120, 50),
        (WIDTH - 200, HEIGHT - (220 + y_offset), 170, 50),
        (WIDTH - 250, HEIGHT - (160 + y_offset), 220, 50),
        (WIDTH - 300, HEIGHT - (100 + y_offset), 270, 50),
    ]
    
    for highlight in highlights:
        draw_highlight(*highlight)
    
    graphics.set_pen(BLACK)
    note = "Hold A + E, then press Reset, to return to the Launcher"
    note_len = graphics.measure_text(note, 2) // 2
    graphics.text(note, (WIDTH // 2 - note_len), HEIGHT - 30, 600, 2)

def handle_button_press(button, state_key):
    """
    Handles a button press event, triggering the appropriate app to launch.

    Parameters:
    - button (object): The button object that is being checked for a press.
    - state_key (str): The key corresponding to the app state in APP_STATES dictionary.

    Returns:
    - None
    """
    app_states = {
        'A': "app_nasa",
        'B': "app_pictures",
        'C': "app_weather",
        'D': "app_news",
        'E': "app_xkcd"
    }
    
    if button.read():
        button.led_on()
        sh.update_state(app_states[state_key])
        time.sleep(0.5)
        reset()

def initalize(graphics, width, height):
    """
    Shows an initialization screen before showing the launcher and in between loading an app.

    Parameters:
    - width: The display width.
    - height: The display height.

    Returns:
    - None
    """
    # Switching to bitmap8 to get upper and lower case letters.
    graphics.set_font("bitmap8")
    
    # Start initializing the display, by showing a temporary message first.
    graphics.set_pen(WHITE)
    graphics.clear()
    graphics.set_pen(BLACK)
    graphics.text("Initializing...", 180, 200, 600, 4)
    
    # Display a short waiting message.
    graphics.set_pen(BLACK)
    note = "Please wait while the display is loading up the Launcher..."
    note_len = graphics.measure_text(note, 2) // 2
    graphics.text(note, (width // 2 - note_len), height - 30, 600, 2)
    graphics.update()

def launcher():
    """
    Main function to start the launcher application. It draws the launcher menu
    and waits for user input to launch an app.

    Parameters:
    - None

    Returns:
    - None
    """
    draw_launcher_menu()
    ih.led_warn.on()
    graphics.update()
    ih.led_warn.off()
    
    while True:
        handle_button_press(ih.inky_frame.button_a, 'A')
        handle_button_press(ih.inky_frame.button_b, 'B')
        handle_button_press(ih.inky_frame.button_c, 'C')
        handle_button_press(ih.inky_frame.button_d, 'D')
        handle_button_press(ih.inky_frame.button_e, 'E')

# If both button A and button E are pressed while reset load init and the launcher.
if ih.inky_frame.button_a.read() and ih.inky_frame.button_e.read():
    launcher()

# Clear LEDs after launcher run.
ih.clear_button_leds()

# Check if json state file exists.
if ih.file_exists("state.json"):
    # Loads the JSON and launches the app.
    sh.load_state()
    sh.launch_app(sh.state['run'])

    # Passes the the graphics object from the launcher to the app.
    sh.app.graphics = graphics
    sh.app.WIDTH = WIDTH
    sh.app.HEIGHT = HEIGHT
else:
    launcher()

# Retrive wifi name and passwort information.
try:
    from config import WIFI_SSID, WIFI_PASSWORD
    ih.network_connect(WIFI_SSID, WIFI_PASSWORD)
except ImportError:
    print("Please fill out config.py in your WiFi credentials.")

# Collect some memory back.
gc.collect()

# Get the selected state from state.json file.
file = ih.file_exists("state.json")

# This main loop executes the update and draw function from the imported app.
while True:
    sh.app.update()
    ih.led_warn.on()
    sh.app.draw()
    ih.led_warn.off()
    ih.sleep(sh.app.UPDATE_INTERVAL)
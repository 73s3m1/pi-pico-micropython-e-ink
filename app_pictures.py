"""
    This app shows offline images from the loaded SD card.
    
    In order to use this app, you need to provide images in the root of the SD card.
    
    The images must be matching the screen dimensions or smaller and must alos be saved as non-progressive jpgs.
"""

import jpegdec
import sdcard
import os
import inky_frame
import random
import gc
import time
import app_state as sh

from machine import Pin, SPI

# The default update interval for this app in minutes.
UPDATE_INTERVAL = 30

# Constants for screen width and height.
WIDTH = None
HEIGHT = None

# Initialize objects.
graphics = None
j = None

# Try to mount the SD card.
sd_spi = SPI(0, sck=Pin(18, Pin.OUT), mosi=Pin(19, Pin.OUT), miso=Pin(16, Pin.OUT))
sd = sdcard.SDCard(sd_spi, Pin(22))

try:
    os.mount(sd, "/sd")
except Exception as e:
    print(f"Error mounting SD card: {e}")
    
    sd = None

# Variable for storing the image title.
image_title = None

# Method to update images files from the SD card and handling errors.
def update():
    # Check if SD card is mounted.
    if sd is None:
        print("SD card not mounted.")
        return
    
    # Turn on busy light.
    inky_frame.led_busy.on()
    
    print("Update image files from SD card...")
    
    # Try to update and handle any error.
    try:
        do_update()
    except Exception as e:
        print(f"Error displaying image: {e}")
    finally:
        # Ensure busy light is turned off even if there's an error.
        inky_frame.led_busy.off()

# Method that updates the images files from the SD card.
def do_update():
    global j, graphics
    
    # Create a new JPEG decoder for our PicoGraphics.
    if j is None:
        j = jpegdec.JPEG(graphics)
    
    # Free some more memory.
    gc.collect()
    
    # Get a list of files that are in the directory.
    files = os.listdir("/sd")
    
    # remove files from the list that aren't .jpgs or .jpegs.
    files = [f for f in files if f.endswith(".jpg") or f.endswith(".jpeg")]
    
    # Count number of files in root directory.
    file_count = len(files)
    
    if file_count == 0:
        print("No JPEG files found on SD card.")
        
        return
    else:
        print(f"Found {file_count} number of files.")
    
    # pick a random file.
    file = files[random.randrange(file_count)]
    
    # Open and decode the JPEG file.
    j.open_file("/sd/" + file)
        
    # Decode the JPEG.
    j.decode(0, 0, jpegdec.JPEG_SCALE_FULL)
    
    # Remove file extension manually and underscores from the filename
    file_name = file
    
    if '.' in file:
        file_name = file[:file.rfind('.')]
    else:
        file_name = file
    
    file_name = file_name.replace("_", " ")
    
    # Print out the filename to the botton right.
    graphics.set_pen(1)
    graphics.rectangle(0, HEIGHT - 25, WIDTH, 25)
    graphics.set_pen(0)
    graphics.text(str(file_name), 5, HEIGHT - 20, WIDTH, 2)

def draw():
    global image_title, graphics
    
    # Display the result.
    if graphics is not None:
        graphics.update()
    
    # Get some memory back, we really need it!
    gc.collect()
    
    # Set next update interval.
    UPDATE_INTERVAL = sh.get_app_update_interval(30, 240)
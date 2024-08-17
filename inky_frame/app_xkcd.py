"""
    This app shows the daily image from XKCD.
    
    In order to use this app, you need to provide a SD card for saving the image.
"""

import gc
import uos
import machine
import jpegdec
import uasyncio
import sdcard
import inky_frame

from machine import Pin, SPI
from urllib import urequest

# The default update interval for this app in minutes.
UPDATE_INTERVAL = 480

# Constants for cache file and endpoint.
FILENAME = "/sd/xkcd-daily.jpg"
ENDPOINT = "https://github.com/73s3m1/pi-pico-micropython-e-ink/blob/main/image/xkcd/xkcd-daily.jpg?raw=true"

print("Load app for daily XKCD message.")

# Initialize objects.
graphics = None

# Free some memory.
gc.collect()

print("Start mounting SD card.")

# Set up the SD card.
sd_spi = SPI(0, sck=Pin(18, Pin.OUT), mosi=Pin(19, Pin.OUT), miso=Pin(16, Pin.OUT))
sd = sdcard.SDCard(sd_spi, Pin(22))

# Try to mount the SD card.
try:
    uos.mount(sd, "/sd")
    
    print("Finished mounting SD card.")
except Exception as e:
    print(f"Error mounting SD card: {e}")
    
    sd = None

# Free some memory.
gc.collect()

def update():
    """
    Update the XKCD image by fetching it from the internet and displaying it.
    Includes error handling and LED indicator for busy status.
    
    Parameters:
    - None

    Returns:
    - None
    """
    # Check if SD card is mounted, if not, skip the update.
    if sd is None:
        print("SD card not mounted.")
        return
    
    # Turn on the busy LED to indicate processing.
    inky_frame.led_busy.on()
    
    print("Update XKCD message and cache it to SD card...")
    
    # Attempt to update the image and handle any errors.
    try:
        do_update()
    except Exception as e:
        print(f"Error displaying XKCD message: {e}")
    finally:
        # Ensure the busy LED is turned off even if there's an error.
        inky_frame.led_busy.off()

def do_update():
    """
    Perform the actual update process by downloading the image and saving it to the SD card.
    This method does not include error handling; it is intended to be called within update().
    
    Parameters:
    - None

    Returns:
    - None
    """
    global graphics
    
    # Get the display bounds from the inky display.
    WIDTH, HEIGHT = graphics.get_bounds()
    
    # Free up memory before displaying the message.
    gc.collect()
    
    # Use the default endpoint URL to retrieve the image.
    url = ENDPOINT
    
    # Open a socket and stream the image data.
    socket = urequest.urlopen(url)
    
    # Create a buffer to store chunks of image data while streaming.
    data = bytearray(1024)
    
    # Save the streamed image data to a file on the SD card.
    with open(FILENAME, "wb") as f:
        while True:
            if socket.readinto(data) == 0:
                break
            f.write(data)
    
    # Close the socket after the image is fully downloaded.
    socket.close()
    
    # Initialize the JPEG decoder with the graphics object.
    jpeg = jpegdec.JPEG(graphics)
    
    # Clear the display before rendering the new image.
    graphics.set_pen(1)
    graphics.clear()

    # Open the saved JPEG file and decode it onto the display.
    jpeg.open_file(FILENAME)
    jpeg.decode()

def draw():
    """
    Render the current graphics buffer to the screen.
    Ensures memory is managed effectively before and after the drawing operation.
    
    Parameters:
    - None

    Returns:
    - None
    """
    print("Draw graphics updates to screen.")
    
    # Free up some more memory before updating the display.
    gc.collect()
    
    # Display the result if graphics object is initialized.
    if graphics is not None:
        graphics.update()
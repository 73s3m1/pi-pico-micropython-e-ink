"""
    This app shows the daily image from XKCD.
    
    In order to use this app, you need to provide a SD card for saving the image.
    
    Fetches a pre-processed XKCD daily image from:
    https://pimoroni.github.io/feed2image/xkcd-daily.jpg
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
ENDPOINT = "https://pimoroni.github.io/feed2image/xkcd-daily.jpg"

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
    # Mount the SD card.
    uos.mount(sd, "/sd")
    
    print("Finished mounting SD card.")
except Exception as e:
    print(f"Error mounting SD card: {e}")
    
    sd = None

# Free some memory.
gc.collect()

# Method to update XKCD message including error handling.
def update():
    # Check if SD card is mounted, we need the SD card.
    if sd is None:
        print("SD card not mounted.")
        return
    
    # Turn on busy light.
    inky_frame.led_busy.on()
    
    print("Update XKCD message and cache it to SD card...")
    
    # Try to update and handle any error.
    try:
        do_update()
    except Exception as e:
        print(f"Error displaying XKCD message: {e}")
    finally:
        # Ensure busy light is turned off even if there's an error.
        inky_frame.led_busy.off()

# Method to perform the message update without error handling.
def do_update():
    global graphics
    
    # Get bounds from the inky display.
    WIDTH, HEIGHT = graphics.get_bounds()
        
    # Free some memory before displaying the message.
    gc.collect()
    
    # Use default endpoint for retrieving message and image.
    url = ENDPOINT
    
    if (WIDTH, HEIGHT) != (600, 448):
        url = url.replace("xkcd-", f"xkcd-{WIDTH}x{HEIGHT}-")
    
    # Open socket and stream image 600x448.
    socket = urequest.urlopen(url)
    
    # Stream the image data from the socket onto disk in 1024 byte chunks,
    # the 600x448-ish jpeg will be roughly ~24k, we really don't have the RAM!
    data = bytearray(1024)
    
    with open(FILENAME, "wb") as f:
        while True:
            if socket.readinto(data) == 0:
                break
            f.write(data)
    
    socket.close()
    
    jpeg = jpegdec.JPEG(graphics)
    
    graphics.set_pen(1)
    graphics.clear()

    jpeg.open_file(FILENAME)
    jpeg.decode()

def draw():
    print("Draw graphics updates to screen.")
    
    # Again free up some more memory.
    gc.collect()
    
    # Display the result.
    if graphics is not None:
        graphics.update()

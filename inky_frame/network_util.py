"""
    MicroPython Network Management
    
    This script provides functionality to control an Inky Frame, including managing network connectivity,
    LED control, and real-time clock (RTC) operations. The main features include controlling LEDs with PWM,
    connecting to Wi-Fi, handling sleep mode, and checking file existence.
    
    This script is based on an example from the getting started guide under https://learn.pimoroni.com/article/getting-started-with-inky-frame.

    Functions:
        - network_led(brightness): Sets the brightness of the network LED with gamma correction.
        - network_led_callback(t): Timer callback to update the network LED brightness in a pulsing pattern.
        - pulse_network_led(speed_hz): Sets the network LED into pulsing mode at the specified speed.
        - stop_network_led(): Turns off the network LED and stops any pulsing animation.
        - sleep(t): Puts the device to sleep for a specified number of minutes using the RTC.
        - clear_button_leds(): Turns off all the button LEDs on the Inky Frame.
        - network_connect(SSID, PSK): Connects to a Wi-Fi network using the provided SSID and password.
        - file_exists(filename): Checks if a file exists and is a regular file (not a directory).
"""

import math
import time
import json
import os
import network
import inky_frame

from pimoroni_i2c import PimoroniI2C
from pcf85063a import PCF85063A
from machine import Pin, PWM, Timer

# Pin setup for VSYS_HOLD needed to sleep and wake.
HOLD_VSYS_EN_PIN = 2
hold_vsys_en_pin = Pin(HOLD_VSYS_EN_PIN, Pin.OUT)

# Initialize the PCF85063A real-time clock (RTC) chip with I2C communication
I2C_SDA_PIN = 4  # Pin for I2C data (SDA)
I2C_SCL_PIN = 5  # Pin for I2C clock (SCL)
i2c = PimoroniI2C(I2C_SDA_PIN, I2C_SCL_PIN, 100000)  # Initialize I2C interface
rtc = PCF85063A(i2c)  # Initialize RTC with I2C interface

# Set up a warning LED on pin 6
led_warn = Pin(6, Pin.OUT)

# Set up for the network LED on pin 7 using PWM
network_led_pwm = PWM(Pin(7))
network_led_pwm.freq(1000)  # Set PWM frequency to 1000 Hz
network_led_pwm.duty_u16(0)  # Initialize with 0 brightness

def network_led(brightness):
    """
    Set the brightness of the network LED with gamma correction.
    
    :param brightness: Brightness level (0-100).
    """
    brightness = max(0, min(100, brightness))  # Clamp brightness to range 0-100
    value = int(pow(brightness / 100.0, 2.8) * 65535.0 + 0.5)  # Apply gamma correction
    network_led_pwm.duty_u16(value)  # Set PWM duty cycle

# Initialize variables for network LED pulsing
network_led_timer = Timer(-1)
network_led_pulse_speed_hz = 1

def network_led_callback(t):
    """
    Timer callback to update the network LED brightness based on a sinusoidal wave.
    
    :param t: Timer object.
    """
    brightness = (math.sin(time.ticks_ms() * math.pi * 2 / (1000 / network_led_pulse_speed_hz)) * 40) + 60
    value = int(pow(brightness / 100.0, 2.8) * 65535.0 + 0.5)
    network_led_pwm.duty_u16(value)

def pulse_network_led(speed_hz=1):
    """
    Set the network LED into pulsing mode.
    
    :param speed_hz: Speed of the pulsing in Hz (default is 1 Hz).
    """
    global network_led_timer, network_led_pulse_speed_hz
    network_led_pulse_speed_hz = speed_hz  # Set the pulsing speed
    network_led_timer.deinit()  # Deinitialize the previous timer
    network_led_timer.init(period=50, mode=Timer.PERIODIC, callback=network_led_callback)  # Initialize timer

def stop_network_led():
    """
    Turn off the network LED and disable any pulsing animation that's running.
    """
    global network_led_timer
    network_led_timer.deinit()  # Deinitialize the timer
    network_led_pwm.duty_u16(0)  # Turn off the LED

def sleep(t):
    """
    Puts the device to sleep for a specified number of minutes.
    
    :param t: Time to sleep in minutes.
    """
    rtc.clear_timer_flag()  # Clear any existing RTC timer flags
    rtc.set_timer(t, ttp=rtc.TIMER_TICK_1_OVER_60HZ)  # Set RTC timer
    rtc.enable_timer_interrupt(True)  # Enable timer interrupt

    hold_vsys_en_pin.init(Pin.IN)  # Set HOLD VSYS pin to input (allow sleep mode)

    time.sleep(60 * t)  # Sleep for the specified time (in seconds)

def clear_button_leds():
    """
    Turns off the LEDs of all buttons on the Inky Frame.
    """
    inky_frame.button_a.led_off()
    inky_frame.button_b.led_off()
    inky_frame.button_c.led_off()
    inky_frame.button_d.led_off()
    inky_frame.button_e.led_off()

def network_connect(SSID, PSK):
    """
    Connects to a Wi-Fi network using the given SSID and PSK.
    
    :param SSID: The SSID (name) of the Wi-Fi network.
    :param PSK: The Pre-Shared Key (password) of the Wi-Fi network.
    """
    wlan = network.WLAN(network.STA_IF)  # Create a WLAN interface instance
    wlan.active(True)  # Activate the WLAN interface

    max_wait = 10  # Maximum wait time for connection (in seconds)

    pulse_network_led()  # Start pulsing the network LED
    wlan.connect(SSID, PSK)  # Attempt to connect to the Wi-Fi network

    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break  # Exit loop if connected or if an error occurred
        max_wait -= 1
        print('waiting for connection...')
        time.sleep(1)  # Wait 1 second before retrying

    stop_network_led()  # Stop pulsing the LED
    network_led_pwm.duty_u16(30000)  # Set the LED to a moderate brightness

    if wlan.status() != 3:
        stop_network_led()  # Ensure pulsing is stopped
        led_warn.on()  # Turn on the warning LED if connection failed

def file_exists(filename):
    """
    Checks if a file exists and is a regular file (not a directory).
    
    :param filename: The path to the file to check.
    :return: True if the file exists and is a regular file, False otherwise.
    """
    try:
        return os.stat(filename)[0] & 0x8000  # Check for regular file (0x8000 indicates a regular file)
    except OSError:
        return False  # Return False if the file does not exist or if an error occurred

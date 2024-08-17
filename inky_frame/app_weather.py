"""
    This app shows currenty weather information.
    
    The weather data is retrieved by OpenWeather API.
    
    Please make sure to fill out the config.py with your API Key.
    
    Do not store your API Key directly in this file.
"""

import jpegdec
import sdcard
import os
import inky_frame
import urequests
import gc
import app_state as sh

from machine import Pin, SPI, ADC
from config import API_KEY, CITY_ID, LAT, LON

# The default update interval for this app in minutes.
UPDATE_INTERVAL = 30

# Initialize objects.
graphics = None

# Try to mount the SD card.
sd_spi = SPI(0, sck=Pin(18, Pin.OUT), mosi=Pin(19, Pin.OUT), miso=Pin(16, Pin.OUT))
sd = sdcard.SDCard(sd_spi, Pin(22))

try:
    os.mount(sd, "/sd")
except Exception as e:
    print(f"Error mounting SD card: {e}")
    
    sd = None

# Method to update images files from the SD card and handling errors.
def update():
    # Check if SD card is mounted.
    if sd is None: 
        print("SD card not mounted.")
        return
    
    # Turn on busy light.
    inky_frame.led_busy.on()
    
    print("Update weather information...")
    
    # Try to update, handle any error and make sure to disable LED.
    try:
        do_update()
    except Exception as e:
        print(f"Error displaying weather information: {e}")
    finally:
        inky_frame.led_busy.off()

# Fetch internal temperatur from Raspberry Pi Pico W (see https://electrocredible.com/raspberry-pi-pico-temperature-sensor-tutorial/)
def fetch_internal_temperature():
    # Create an ADC instance to read the voltage from the fifth channel.
    adc = ADC(4)
    
    try:
        # First, we need to read 16 digital bits of data wiht read_u16.
        # Then, we need to get a reading in the range of 0 to 65535 for a voltage range of 0V to 3.3V.
        # We then scale into the voltage range between 0V to 3.3V.
        adc_voltage = adc.read_u16() * (3.3 / 65536)
        
        # Based on the upper equation, we need to calculate the value for temperature in Celcius.
        # Typically, Vbe = 0.706V at 27 degrees C, with a slope of -1.721mV per degree.
        # Therefore the temperature can be approximated as follows: 27 - (adc_voltage - 0.706) / 0.001721
        # This formular can be found in https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf in section 4.9.5 "Temperature Sensor".
        temp = 27 - (adc_voltage - 0.706) / 0.001721
        
        return temp
    except Exception as e:
        print(f"Error fetching temperature data: {e}")
        return None

# Method to fetch weather information.
def fetch_weather():
    try:
        # Weather URL from openweathermap.
        url = f"http://api.openweathermap.org/data/2.5/weather?id={CITY_ID}&lang=de&appid={API_KEY}&units=metric"
        
        # Send GET request to the weather API.
        response = urequests.get(url)
        data = response.json()
        response.close()
        
        # Extract weather data.
        name = data['name']
        temp = data['main']['temp']
        feels = data['main']['feels_like']
        weather_description = data['weather'][0]['description']
        icon = data['weather'][0]['icon']
        humidity = data['main']['humidity']
        
        # Return the extracted data.
        return name, temp, feels, weather_description, icon, humidity
    except Exception as e:
        print(f"Error fetching weather data: {e}")
        return None, None, None, None, None, None

# Method to fetch the weather forecast
def fetch_forecast():
    try:
        # Weather URL from OpenWeatherMap API
        url = f"http://api.openweathermap.org/data/2.5/forecast?lat={LAT}&lon={LON}&cnt=3&appid={API_KEY}&units=metric"
        
        # Send GET request to the forecast API
        response = urequests.get(url)
        data = response.json()
        response.close()
        
        # Extract forecast data.
        forecast_list = data['list']
        forecast_data = []
        
        for forecast in forecast_list:
            temp = forecast['main']['temp']
            weather_description = forecast['weather'][0]['description']
            icon = forecast['weather'][0]['icon']
            humidity = forecast['main']['humidity']
            wind_speed = forecast['wind']['speed']
            wind_gust = forecast.get('wind', {}).get('gust', None)
            wind_deg = forecast['wind']['deg']
            dt_txt = forecast['dt_txt']
            
            date_txt = dt_txt.split(' ')[0]
            time_txt = dt_txt.split(' ')[1]
            
            # Store the extracted data in a dictionary.
            forecast_data.append({
                'temp': temp,
                'description': weather_description,
                'icon': icon,
                'humidity': humidity,
                'wind_speed': wind_speed,
                'wind_gust': wind_gust,
                'wind_deg': wind_deg,
                'date': date_txt,
                'time': time_txt
            })
        
        return forecast_data
    except Exception as e:
        print(f"Error fetching weather data: {e}")
        return []

def interpolate_color(min_temp, max_temp, current_temp, color1, color2):
    ratio = (current_temp - min_temp) / (max_temp - min_temp)
    ratio = max(0, min(1, ratio))
    
    r = int(color1[0] + ratio * (color2[0] - color1[0]))
    g = int(color1[1] + ratio * (color2[1] - color1[1]))
    b = int(color1[2] + ratio * (color2[2] - color1[2]))
    
    return (r, g, b)

def get_temperature_color(temp_celsius):
    cold_color = (0, 0, 255)
    warm_color = (255, 165, 0)
    
    min_temp = 0
    max_temp = 35
    
    return interpolate_color(min_temp, max_temp, temp_celsius, cold_color, warm_color)

# Method that updates the images files from the SD card.
def do_update():
    name, temp, feels, description, icon, humidity = fetch_weather()
    
    if temp is None:
        print("Failed to retrieve weather data.")
        return
    
    int_temp_c = fetch_internal_temperature()
    
    # Make sure to clean up memory before proceeding.
    gc.collect()
    
    # Set pen to white.
    graphics.set_pen(1)
    
    # Clear the display.
    graphics.clear()
    
    # Display icon for weather status.
    try:
        # Open and display status symbol.
        jpeg = jpegdec.JPEG(graphics)
        
        jpeg.open_file("/status/" + icon + ".jpg")
        jpeg.decode(WIDTH - 240, 0)
    except OSError:
        print("Failed to retrieve status icon.")
    
    # Make sure to clean up memory before proceeding.
    gc.collect()
    
    # Set pen to black.
    graphics.set_pen(0)
    
    # Choose a font.
    graphics.set_font("bitmap8")
    
    # Display the weather information.
    graphics.text(f"{name}, Heute", 10, 10, scale=4)
    graphics.text(f"Fühlt sich an wie {feels}", 10, 140)
    graphics.text(f"{description}", 10, 160)
    graphics.text(f"Die Luftfeuchtigkeit liegt bei {humidity}%", 10, 180)
    
    if int_temp_c is not None:
        graphics.text(f"Raumtemparatur: {int_temp_c:.2f} C", 10, 200)
    
    # Get some memory back, we really need it!
    gc.collect()
    
    # Print out the temperature.
    color = get_temperature_color(temp)
    
    graphics.set_pen(graphics.create_pen(color[0], color[1], color[2]))
    
    graphics.text(f"{temp}°C", 10, 60, scale=8)
    
    # Set pen back to black.
    graphics.set_pen(0)
    
    # Get some memory back, we really need it!
    gc.collect()
    
    # Print out forecast for the next three days.
    forecast = fetch_forecast()
    day_number = 0
    
    for day in forecast:
        graphics.text(f"{day['date']}", 50 + (200 * day_number), HEIGHT - 180, scale=2)
        graphics.text(f"{day['time']}", 60 + (200 * day_number), HEIGHT - 160, scale=2)
        graphics.text(f"{day['temp']}°C", 70 + (200 * day_number), HEIGHT - 30, scale=2)
        
        # Print out the status icon.
        try:
            # Open and display status symbol.
            if jpeg is None:
                jpeg = jpegdec.JPEG(graphics)
            
            jpeg.open_file("/status/" + day['icon'] + ".jpg")
            jpeg.decode(40 + (200 * day_number), HEIGHT - 140, jpegdec.JPEG_SCALE_HALF, dither=True)
            
            day_number = day_number + 1
        except OSError:
            print("Failed to retrieve status icon.")
        
        # Make sure to clean up memory before proceeding.
        gc.collect()

def draw():
    # Display the result.
    if graphics is not None:
        graphics.update()
    
    # Set next update interval.
    UPDATE_INTERVAL = sh.get_app_update_interval(10, 120)

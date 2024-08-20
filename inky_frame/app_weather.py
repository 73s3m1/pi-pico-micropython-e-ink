"""
    Weather Display Application for Raspberry Pi Pico W.

    This application fetches and displays current weather information
    and a short-term weather forecast using the OpenWeather API.

    Dependencies:
    - jpegdec
    - urequests
    - inky_frame

    Configuration:
    - API_KEY: Your OpenWeather API key.
    - LAT, LON: Latitude and longitude for fetching weather forecast.
    - LANG: Language setting for weather API.
    - UNIT: The unit used for the weather API (metric, imperial, etc.).

    Usage:
    In order to use this app you need to create an openweathermap API account.
    Additionally, you need to ensure you have an active Wifi-Connection, please provide your Wifi details in your config.py file.
    This account needs to be specified within the config.py configuration file.
    Please make also sure to provide the status folder to the root of the Raspberry Pi Pico W.

    The LAT and LON are used for the weather forecast and the current weather.
    You can use Google maps to retrive your local LAT and LON.
"""

import jpegdec
import os
import inky_frame
import urequests
import gc
import app_state as sh

from machine import Pin, SPI, ADC
from config import API_KEY, LOCATION_NAME, LAT, LON, LANG, UNIT

# The default update interval for this app in minutes.
UPDATE_INTERVAL = 30

# Initialize global variables.
graphics = None

def update():
    """
    Main update function to fetch and display weather data.
    """
    # Turn on busy light indicator.
    inky_frame.led_busy.on()

    print("Update weather information...")

    try:
        do_update()
    except Exception as e:
        print(f"Error displaying weather information: {e}")
    finally:
        # Ensure the busy light is turned off.
        inky_frame.led_busy.off()

def fetch_internal_temperature():
    """
    Fetches the internal temperature of the Raspberry Pi Pico W. Keep in mind that the internal temperature reading might be off.

    Further information can be found under https://electrocredible.com/raspberry-pi-pico-temperature-sensor-tutorial/.
    More information for the calculation can be found under  https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf.

    Returns:
        float: The temperature in Celsius.
    """
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

def fetch_weather(lat, lon, lang, api_key, unit):
    """
    Fetches current weather data from OpenWeather API.

    Returns:
        tuple: Weather data (name, temp, feels_like, description, icon, humidity).
    """
    try:
        # Fixed weather URL from openweathermap.
        url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&lang={lang}&appid={api_key}&units={unit}"

        # Send GET request to the weather API.
        response = urequests.get(url)
        data = response.json()
        response.close()

        # Extract weather data.
        name = data['name']
        temp = data['main']['temp']
        feels = data['main']['feels_like']
        description = data['weather'][0]['description']
        icon = data['weather'][0]['icon']
        humidity = data['main']['humidity']

        return name, temp, feels, description, icon, humidity
    except Exception as e:
        print(f"Error fetching weather data: {e}")
        return None, None, None, None, None, None

def fetch_forecast(lat, lon, api_key, unit):
    """
    Fetches a 3-point weather forecast from the OpenWeather API for the next 3 intervals (3 hour, 6 hour and 9 hour forecast).

    Returns:
        list: A list of dictionaries containing forecast data.
    """
    try:
        # The following URL is used for the weather forecast on the botton of the screen (limited to 3 data points).
        # The amount of data points is therefore limited to 3, this prevents an out of memory message for retriving to much data at a time.
        url = f"http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&cnt=3&appid={api_key}&units={unit}"

        # Send GET request to the forecast API.
        response = urequests.get(url)
        data = response.json()
        response.close()

        # Extract forecast data.
        forecast_list = data['list']
        forecast_data = []

        for forecast in forecast_list:
            temp = forecast['main']['temp']
            description = forecast['weather'][0]['description']
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
                'description': description,
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
        print(f"Error fetching weather forecast data: {e}")
        return []

def interpolate_color(min_temp, max_temp, current_temp, color1, color2):
    """
    Interpolates between two colors based on the current temperature.

    Args:
        min_temp (float): Minimum temperature for interpolation.
        max_temp (float): Maximum temperature for interpolation.
        current_temp (float): Current temperature.
        color1 (tuple): RGB color for the minimum temperature.
        color2 (tuple): RGB color for the maximum temperature.

    Returns:
        tuple: Interpolated RGB color.
    """
    ratio = (current_temp - min_temp) / (max_temp - min_temp)
    ratio = max(0, min(1, ratio))

    r = int(color1[0] + ratio * (color2[0] - color1[0]))
    g = int(color1[1] + ratio * (color2[1] - color1[1]))
    b = int(color1[2] + ratio * (color2[2] - color1[2]))

    return (r, g, b)

def get_temperature_color(temp_celsius):
    """
    Determines the display color based on the current temperature.

    Args:
        temp_celsius (float): Temperature in Celsius.

    Returns:
        tuple: RGB color corresponding to the temperature.
    """
    # Blue for cold temperatures.
    cold_color = (120, 160, 255)
    
    intermediate_color = (30, 30, 30)
    
    # Red for warm temperatures.
    warm_color = (255, 0, 0)

    min_temp = 0
    max_temp = 30

    return interpolate_color(min_temp, max_temp, temp_celsius, cold_color, warm_color)

def do_update():
    """
    Fetches and displays weather information on the Inky Frame display.
    """
    name, temp, feels, description, icon, humidity = fetch_weather(LAT, LON, LANG, API_KEY, UNIT)

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
        jpeg.decode(WIDTH - 240, 0, jpegdec.JPEG_SCALE_FULL, dither=True)
    except OSError:
        print("Failed to retrieve status icon.")

    # Make sure to clean up memory before proceeding.
    gc.collect()

    # Set pen to black.
    graphics.set_pen(0)

    # Choose a font.
    graphics.set_font("bitmap8")

    # Display the weather information.
    graphics.text(f"{LOCATION_NAME}, Heute", 10, 10, scale=4)
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
    forecast = fetch_forecast(LAT, LON, API_KEY, UNIT)
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
    """
    Displays the final graphics on the Inky Frame display.
    """
    if graphics is not None:
        graphics.update()

    # Set next update interval.
    UPDATE_INTERVAL = sh.get_app_update_interval(30, 120)
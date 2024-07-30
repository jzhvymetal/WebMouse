import asyncio
import socketpool
import wifi
import json
import usb_hid
from adafruit_hid.mouse import Mouse
import math
import os
import sys

from adafruit_httpserver import Server, Request, Response, GET, POST, PUT, FileResponse


WIFI_SSID = os.getenv("CIRCUITPY_WIFI_SSID")
WIFI_PASS = os.getenv("CIRCUITPY_WIFI_PASSWORD")

wifi.radio.enabled = True
while(True): #WIFI Connect Loop
    if wifi.radio.connected:
        print("WIFI: Connected with IP=" + str(wifi.radio.ipv4_address))
        break
    else:
        print("WIFI: Connecting to " + WIFI_SSID)
        try:
            wifi.radio.connect(WIFI_SSID, WIFI_PASS)
        except Exception as e:
            print("HOST: Exception " + str(e)  + "...Retry in 3s")
            time.sleep(3)


pool = socketpool.SocketPool(wifi.radio)
server = Server(pool, "/www" , debug=True)
dict_data={}

mouse = Mouse(usb_hid.devices)


@server.route("/mouse")
def client(request: Request):
    return FileResponse(request, "mouse.htm", "/")


@server.route("/api", [POST, PUT], append_slash=True)
def api(request: Request):
    global dict_data
    # Upload or update objects
    if request.method in [POST, PUT]:
        dict_data=uploaded_object = request.json()
        print(dict_data)    
    

server.start(str(wifi.radio.ipv4_address))


async def handle_http_requests():
    while True:
        try:
            server.poll()
        except Exception as e:
            print("Error-handle_http_request:", str(e))
        await asyncio.sleep(0.1)

async def handle_mouse():
    global dict_data

    # Constants for acceleration
    MAX_COUNTER = 50  # Maximum value for the counter
    START_MOVE_DISTANCE = 1  # Initial movement distance
    FULL_MOVE_DISTANCE = 10  # Maximum movement distance
    COUNTER_INCREMENT = 0.1  # Increment the counter by 1 per tick
    DECAY_FACTOR = 1  # Amount to decrease the counter per tick when no movement is detected
    DIRECTION_SMOOTHING = 0.1  # Smoothing factor for direction changes

    counter = 0  # Initialize the counter
    direction_x, direction_y = 0, 0  # Current direction with smoothing

    while True:
        try:
            if dict_data:
                # Calculate the new direction with smoothing
                new_x, new_y = dict_data['x'], dict_data['y']
                direction_x = direction_x * (1 - DIRECTION_SMOOTHING) + new_x * DIRECTION_SMOOTHING
                direction_y = direction_y * (1 - DIRECTION_SMOOTHING) + new_y * DIRECTION_SMOOTHING

                if new_x != 0 or new_y != 0:
                    # Increment counter based on movement
                    counter = min(counter + COUNTER_INCREMENT, MAX_COUNTER)
                else:
                    # Gradually decay the counter when there's no movement
                    counter = max(counter - DECAY_FACTOR, 0)
                
                # Calculate the current acceleration factor based on the counter
                acceleration_factor = counter / MAX_COUNTER
                
                # Scale START_MOVE_DISTANCE to FULL_MOVE_DISTANCE
                move_distance = START_MOVE_DISTANCE + (FULL_MOVE_DISTANCE - START_MOVE_DISTANCE) * acceleration_factor
                
                # Base movement distances
                move_x = direction_x * move_distance
                move_y = direction_y * move_distance
                
                # Apply acceleration to movement distances
                accel_x = move_x
                accel_y = move_y
                
                # Ensure integer values for mouse.move
                mouse.move(x=int(accel_x), y=int(-accel_y))
        except Exception as e:
            print("Error-handle_mouse:", str(e))
            
        # Sleep to simulate time passing and give an effect of incremental ramp-up
        await asyncio.sleep(0.01)


async def main():
    await asyncio.gather(
        asyncio.create_task(handle_http_requests()),
        asyncio.create_task(handle_mouse())
    )

asyncio.run(main())

from asyncio import create_task, gather, run, sleep as async_sleep
import socketpool
import wifi
import json
import usb_hid
from adafruit_hid.mouse import Mouse
import math
import os

from adafruit_httpserver import Server, Request, Response, Websocket, GET, FileResponse


WIFI_SSID = os.getenv("CIRCUITPY_WIFI_SSID")
WIFI_PASS = os.getenv("CIRCUITPY_WIFI_PASSWORD")


while(True): #WIFI Connect Loop
    wifi_connected = wifi.radio.ap_info is not None
    if wifi_connected:
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

websocket: Websocket = None
mouse = Mouse(usb_hid.devices)

@server.route("/connect-websocket", GET)
def connect_client(request: Request):
    global websocket  
    if websocket is not None:
        websocket.close()  # Close any existing connection
    websocket = Websocket(request)
    return websocket

@server.route("/mouse")
def client(request: Request):
    return FileResponse(request, "mouse.htm", "/")

server.start(str(wifi.radio.ipv4_address))


async def handle_http_requests():
    while True:
        server.poll()
        await async_sleep(0.1)


async def handle_websocket_requests():
    while True:
        global dict_data
        if websocket is not None:
            if (data := websocket.receive(fail_silently=True)) is not None:
                dict_data=json.loads(data)
                #print(dict_data)
        await async_sleep(0.001)

async def handle_mouse():
    global dict_data
    global mouse_accel_dur
    global mouse_move_active
    global mouse_move_start
    global mouse_move_max
    global mouse_moving

    while True:
        if dict_data:
            if not mouse_moving:
                mouse_move_active=0
                if (dict_data['x']!=0 or dict_data['y']!=0) : 
                    mouse_moving=True;
                else:
                    mouse_moving=False;    
            
            if mouse_moving: # 2nd if required not else
                mouse.move(x=int(dict_data['x']*mouse_move_active), y=int(-dict_data['y']*mouse_move_active))
                mouse_move_active=mouse_move_active+1

        await async_sleep(0.01)
        

import math

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
        
        # Sleep to simulate time passing and give an effect of incremental ramp-up
        await async_sleep(0.01)


async def main():
    await gather(
        create_task(handle_http_requests()),
        create_task(handle_websocket_requests()),
        create_task(handle_mouse())
    )

try:
	run(main())
except Exception as e:
    print("Error:\n", str(e))

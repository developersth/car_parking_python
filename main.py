import os
from dotenv import load_dotenv

load_dotenv()

MQTT_HOST = os.getenv('MQTT_HOST')
MQTT_PORT = os.getenv('MQTT_PORT')
MQTT_USER = os.getenv('MQTT_USER')
MQTT_PASS = os.getenv('MQTT_PASS')

print([MQTT_HOST, MQTT_PORT, MQTT_USER, MQTT_PASS])

import time
from cMQTTClient import *
from cVehicleCounter import *

# Example usage
mqtt_client = MQTTClient(broker_address=MQTT_HOST, port=MQTT_PORT, username=MQTT_USER, password=MQTT_PASS)
mqtt_client.connect()
time.sleep(1.0)

while not mqtt_client.connected:
    mqtt_client.reconnect()

counter = VehicleCounter(camera_name="b-in", source="D:\\CarPark\\ZONE B-IN\\Camera1_VR-20241025-110855.mp4", view_img=True, save_img=True)
counter.run(mqtt_client)

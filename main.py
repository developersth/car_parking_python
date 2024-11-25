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
from cManagementCounter import *

def get_video_files(directory):
    # Common video file extensions
    video_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.mpeg', '.mpg', '.webm', '.m4v', '.3gp', '.vob'}
    video_files = []

    # Walk through all files in the directory and subdirectories
    for root, _, files in os.walk(directory):
        for file in files:
            # Check if the file has a video extension
            if os.path.splitext(file)[1].lower() in video_extensions:
                video_files.append(os.path.join(root, file))
    
    return video_files

def ensure_path_exists(path):
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        print(f"Path ensured: {path}")
    except OSError as e:
        print(f"Error creating path: {e}")

mqtt_client = None

# # Example usage
# mqtt_client = MQTTClient(broker_address=MQTT_HOST, port=MQTT_PORT, username=MQTT_USER, password=MQTT_PASS)
# mqtt_client.connect()
# time.sleep(1.0)

# while not mqtt_client.connected:
#     mqtt_client.reconnect()

view_img=True
# processList = ["D:\\CarPark\\MG", "D:\\CarPark\\LAB-OUT", "D:\\CarPark\\ZONE A", "D:\\CarPark\\ZONE B-IN", "D:\\CarPark\\ZONE B-OUT"]
# processList = ["D:\\CarPark\\LAB-OUT", "D:\\CarPark\\ZONE A", "D:\\CarPark\\ZONE B-IN", "D:\\CarPark\\ZONE B-OUT"]
processList = ["D:\\CarPark\\MG"]

for folder in processList:
    vdoList = get_video_files(directory=folder)
    camName = "cam_" + folder.split('\\')[2].replace('ZONE ', "").lower()
    resultFolder = folder.split('\\')[:-1]
    resultFolder[0] += '\\'
    resultFolder.append(camName)
    resultFolder = os.path.join(*resultFolder)
    ensure_path_exists(resultFolder)

    for fName in vdoList:
        # print(fName)
        # if "Camera2_VR-20241025-111430" in fName:
            if "mg" in camName:
                save_dir = Path(f"D:\\CarPark\\{camName}")
                save_dir.mkdir(parents=True, exist_ok=True)

                # Path to your video file and output file
                input_video_path = fName  # change this to your input video path
                output_video_path = str(save_dir / f"{Path(fName).stem}.mp4")
                debug_video_path = str(save_dir / f"debug_{Path(fName).stem}.mp4")

                print([input_video_path, output_video_path])

                # Create an instance of YOLOCarCounter and process the video
                car_counter = cManagementCounter(input_video_path, output_video_path, debug_video_path, model_path="yolov10x.pt", view_img=view_img)
                car_counter.process_video()
                car_counter.release_resources()
            else:
                counter = VehicleCounter(camera_name=camName, source=fName, view_img=view_img, save_img=True)
                counter.run(mqtt_client)


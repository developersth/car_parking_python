import os
from dotenv import load_dotenv
from pathlib import Path
import time
from cVehicleCounter import VehicleCounter
import signal
import sys
import argparse

load_dotenv()

# Load environment variables for RTSP credentials
RTSP_USER = os.getenv('RTSP_USER')
RTSP_PASS = os.getenv('RTSP_PASS')
RTSP_MG_USER = os.getenv('RTSP_MG_USER')
RTSP_MG_PASS = os.getenv('RTSP_MG_PASS')

def ensure_path_exists(path):
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        print(f"Path ensured: {path}")
    except OSError as e:
        print(f"Error creating path: {e}")

# view_img = True

# Define your RTSP URLs here with username and password
rtsp_urls = {
    "cam_mg": f"rtsp://{RTSP_MG_USER}:{RTSP_MG_PASS}@192.168.1.51",
    "cam_lab-out": f"rtsp://{RTSP_USER}:{RTSP_PASS}@192.168.1.31",
    "cam_main": f"rtsp://{RTSP_USER}:{RTSP_PASS}@192.168.1.11",
    "cam_b-in": f"rtsp://{RTSP_USER}:{RTSP_PASS}@192.168.1.22",
    "cam_b-out": f"rtsp://{RTSP_USER}:{RTSP_PASS}@192.168.1.21",
    "cam_center": f"rtsp://{RTSP_USER}:{RTSP_PASS}@192.168.1.52"
}

class MyEvent:
    def __init__(self):
        self.stop_event = False

# Flag to signal threads to stop
stop_event = MyEvent()
print('stop_event: ', stop_event.stop_event)

def run_camera(camName, rtsp_url, view_img=True):
    global stop_event
    resultFolder = f"D:\\CarPark\\rtsp\\{camName}"
    ensure_path_exists(resultFolder)

    # Create an instance of VehicleCounter and process the RTSP stream
    counter = VehicleCounter(camera_name=camName, source=rtsp_url, view_img=view_img, save_img=True)
    counter.run(stop_event)  # Pass the stop_event to the run method

def signal_handler(sig, frame):
    global stop_event
    print('You pressed Ctrl+C!')
    stop_event.stop_event = True
    print('stop_event: ', stop_event.stop_event)
    sys.exit(0)

# Set up the signal handler
signal.signal(signal.SIGINT, signal_handler)

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Run vehicle counter for a specific camera.")
parser.add_argument('--camera', type=str, required=True, help="Name of the camera to run (e.g., cam_b-out)")
# parser.add_argument('--view_img', type=bool, default=False, help="Whether to view the image (default: True)")
parser.add_argument('--view-img', action='store_true', help="Whether to view the image (default: False)")
args = parser.parse_args()
print(args)

# Check if the provided camera name exists in the rtsp_urls dictionary
if args.camera in rtsp_urls:
    camName = args.camera
    rtsp_url = rtsp_urls[camName]
    # view_img = args.view_img
    print(args.view_img)
    run_camera(camName, rtsp_url, view_img=args.view_img)
else:
    print(f"Camera '{args.camera}' not found. Available cameras: {', '.join(rtsp_urls.keys())}")
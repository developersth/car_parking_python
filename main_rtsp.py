import os
from dotenv import load_dotenv
from pathlib import Path
import time
from cVehicleCounter import VehicleCounter
import signal
import sys
import argparse
from datetime import datetime, timedelta # Import for date calculations

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
    # counter.run_monitor(stop_event)
 
def delete_old_log_files(base_log_dir, days_old=30):
    """
    Deletes log files older than a specified number of days from camera directories.

    Args:
        base_log_dir (str): The base directory where camera log folders are located (e.g., D:\\CarPark\\rtsp).
        days_old (int): The age in days beyond which files should be deleted.
    """
    cutoff_time = datetime.now() - timedelta(days=days_old)
    print(f"\n--- Starting log file cleanup (older than {days_old} days) ---")
    print(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Cutoff time: {cutoff_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base log directory: {base_log_dir}")


    for camName in rtsp_urls.keys():
        camera_log_path = Path(base_log_dir) / camName
        if camera_log_path.is_dir():
            print(f"Checking {camera_log_path} for old files...")
            deleted_count = 0
            for root, _, files in os.walk(camera_log_path):
                for file in files:
                    file_path = Path(root) / file
                    try:
                        # Get modification time of the file
                        file_mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if file_mod_time < cutoff_time:
                            os.remove(file_path)
                            print(f"Deleted: {file_path}")
                            deleted_count += 1
                    except OSError as e:
                        print(f"Error deleting {file_path}: {e}")
            if deleted_count == 0:
                print(f"No old files found in {camera_log_path}.")
            else:
                print(f"Cleaned {deleted_count} old files from {camera_log_path}.")
        else:
            print(f"Camera log directory not found: {camera_log_path}")
    print("--- Log file cleanup complete ---\n")


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
parser.add_argument('--view-img', action='store_true', help="Whether to view the image (default: False)")
args = parser.parse_args()
print(args)

# Check if the provided camera name exists in the rtsp_urls dictionary
if args.camera in rtsp_urls:
    camName = args.camera
    rtsp_url = rtsp_urls[camName]
    
    # --- Integrate log file deletion here ---
    base_log_directory = "D:\\CarPark\\rtsp" # Adjust this to your actual log directory
    delete_old_log_files(base_log_directory, days_old=30)
    # ----------------------------------------

    print(args.view_img)
    run_camera(camName, rtsp_url, view_img=args.view_img)
else:
    print(f"Camera '{args.camera}' not found. Available cameras: {', '.join(rtsp_urls.keys())}")
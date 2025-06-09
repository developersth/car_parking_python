import os
import time
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime, timedelta
from cVehicleCounter import VehicleCounter
import signal
import sys
import argparse
import threading

load_dotenv()

# Load environment variables for RTSP credentials
RTSP_USER = os.getenv('RTSP_USER')
RTSP_PASS = os.getenv('RTSP_PASS')
RTSP_MG_USER = os.getenv('RTSP_MG_USER')
RTSP_MG_PASS = os.getenv('RTSP_MG_PASS')

# Define your RTSP URLs here
rtsp_urls = {
    "cam_mg": f"rtsp://{RTSP_MG_USER}:{RTSP_MG_PASS}@192.168.1.51",
    "cam_lab-out": f"rtsp://{RTSP_USER}:{RTSP_PASS}@192.168.1.31",
    "cam_main": f"rtsp://{RTSP_USER}:{RTSP_PASS}@192.168.1.11",
    "cam_b-in": f"rtsp://{RTSP_USER}:{RTSP_PASS}@192.168.1.22",
    "cam_b-out": f"rtsp://{RTSP_USER}:{RTSP_PASS}@192.168.1.21",
    "cam_center": f"rtsp://{RTSP_USER}:{RTSP_PASS}@192.168.1.52"
}

# Ensures a directory exists
def ensure_path_exists(path):
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        print(f"Path ensured: {path}")
    except OSError as e:
        print(f"Error creating path: {e}")

# Flag to control stop
class MyEvent:
    def __init__(self):
        self.stop_event = False

stop_event = MyEvent()

# Run camera capture
def run_camera(camName, rtsp_url, view_img=True):
    global stop_event
    resultFolder = f"D:\\CarPark\\rtsp\\{camName}"
    ensure_path_exists(resultFolder)

    counter = VehicleCounter(camera_name=camName, source=rtsp_url, view_img=view_img, save_img=True)
    counter.run(stop_event)

# Function to delete old log files based on filename date
def delete_old_log_files_by_filename(base_log_dir, days_old=30):
    cutoff_date = datetime.now() - timedelta(days=days_old)
    print(f"\n--- Cleaning up files older than {cutoff_date.date()} ---")

    deleted_count = 0
    for file in Path(base_log_dir).glob("*.mp4"):
        try:
            date_str = file.name.split("_")[0]
            file_date = datetime.strptime(date_str, "%Y%m%d")
            if file_date < cutoff_date:
                file.unlink()
                print(f"Deleted: {file.name}")
                deleted_count += 1
        except Exception as e:
            print(f"Failed to process {file.name}: {e}")

    print(f"Deleted {deleted_count} files from {base_log_dir}")
    print("--- Cleanup complete ---\n")


# Background task to run cleanup every day at 04:01
def daily_log_cleanup_task(base_log_dir, days_old=30):
    while True:
        now = datetime.now()
        next_run = (now + timedelta(days=1)).replace(hour=4, minute=1, second=0, microsecond=0)
        wait_seconds = (next_run - now).total_seconds()
        print(f"[Cleanup Scheduler] Next cleanup at {next_run}, waiting {int(wait_seconds)} seconds")
        time.sleep(wait_seconds)

        print("[Cleanup Scheduler] Running daily log cleanup...")
        delete_old_log_files_by_filename(base_log_dir, days_old)

# Handle Ctrl+C
def signal_handler(sig, frame):
    global stop_event
    print('You pressed Ctrl+C!')
    stop_event.stop_event = True
    print('stop_event: ', stop_event.stop_event)
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# Parse arguments
parser = argparse.ArgumentParser(description="Run vehicle counter for a specific camera.")
parser.add_argument('--camera', type=str, required=True, help="Name of the camera to run (e.g., cam_b-out)")
parser.add_argument('--view-img', action='store_true', help="Whether to view the image (default: False)")
args = parser.parse_args()

# Main execution
if args.camera in rtsp_urls:
    camName = args.camera
    rtsp_url = rtsp_urls[camName]
    base_log_directory = "D:\\CarPark\\rtsp"

    # 🔁 Start background cleanup thread
    cleanup_thread = threading.Thread(target=daily_log_cleanup_task, args=(base_log_directory, 30), daemon=True)
    cleanup_thread.start()

    # 🧹 Run initial cleanup once
    delete_old_log_files_by_filename(base_log_directory, days_old=30)

    # 📹 Start camera
    run_camera(camName, rtsp_url, view_img=args.view_img)
else:
    print(f"Camera '{args.camera}' not found. Available cameras: {', '.join(rtsp_urls.keys())}")

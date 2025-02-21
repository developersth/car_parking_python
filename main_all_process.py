import subprocess

# List of camera names
cameras = [
    "cam_lab-out",
    "cam_main",
    "cam_b-in",
    "cam_b-out",
    "cam_mg",
    "cam_center"
    # Add more camera names as needed
]

# python .\main_rtsp.py --camera cam_main --view-img
# Function to run the command for each camera
def run_camera_processes():
    processes = []
    for camera in cameras:
        addon = ' --view-img'
        # if 'lab-out' in camera:
        #     addon = ''
        command = f"python .\main_rtsp.py --camera {camera}{addon}"
        process = subprocess.Popen(command, shell=True)
        processes.append(process)
    return processes

if __name__ == "__main__":
    processes = run_camera_processes()
    
    print(f"Started {len(processes)} camera processes.")
    
    # Optionally, you can wait for all processes to complete
    for process in processes:
        process.wait()
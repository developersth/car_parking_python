import requests
import json

class DeviceStatusUpdater:
    def __init__(self, server_url):
        """
        Initialize the DeviceStatusUpdater with the server URL.
        :param server_url: str, the base URL of the server (e.g., "http://your-server:5000")
        """
        self.server_url = server_url.rstrip('/') + "/event"

    def send_status(self, camera, detail):
        """
        Send a status update for a specific device.
        :param camera: str, device identifier (e.g., "cctv1", "led1")
        :param detail: str, new status value ("online" or "offline")
        :return: dict, server response
        """
        payload = {
            "gate": "all",
            "event": "update_device_status",
            "camera": camera,
            "detail": detail
        }
        
        headers = {"Content-Type": "application/json"}
        
        try:
            response = requests.post(self.server_url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()  # Raise an error for HTTP error responses
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

# Example usage:
if __name__ == "__main__":
    server_url = "http://localhost:5000"  # Replace with actual server URL
    updater = DeviceStatusUpdater(server_url)
    response = updater.send_status("cctv1", "online")
    print(response)

import requests
import json, time

class APIClient:
    def __init__(self, base_url):
        self.base_url = base_url

    def post_event(self, gate, event, camera):
        url = f"{self.base_url}/event"
        payload = {
            "gate": gate,
            "event": event,
            "camera": camera
        }
        headers = {'Content-Type': 'application/json'}
        # print(url, payload)
        try:
            response = requests.post(url, data=json.dumps(payload), headers=headers)
            response.raise_for_status()  # Raise an exception for 4xx/5xx responses
            
            # If the response is in JSON format, return it
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return None

    def get_event(self, gate, event, camera):
        url = f"{self.base_url}/event"
        payload = {
            "gate": gate,
            "event": event,
            "camera": camera
        }
        headers = {'Content-Type': 'application/json'}

        try:
            response = requests.get(url, params=payload, headers=headers)
            response.raise_for_status()  # Raise an exception for 4xx/5xx responses
            
            # If the response is in JSON format, return it
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return None

if __name__ == "__main__":
    client = APIClient('http://127.0.0.1:5000')  # Your Flask server URL
    
    try:
        while True:
            # Example for a "car enter" event
            response = client.post_event('a', 'in', 'camera1')
            if response:
                print("Event processed successfully:", response)
            else:
                print("Failed to process event.")
            
            time.sleep(1.0)  # Wait for 1 second before posting again
    
    except KeyboardInterrupt:
        print("\nProcess interrupted. Exiting...")
    
    # Example for a "get" event (checking status)
    # response = client.post_event('all', 'get', 'camera1')
    # if response:
    #     print("Parking lot status:", response)
    # else:
    #     print("Failed to retrieve status.")

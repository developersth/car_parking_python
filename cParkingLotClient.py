import requests

class ParkingLotClient:
    def __init__(self, base_url):
        self.base_url = base_url

    def get_available_slots(self):
        url = f'{self.base_url}/event'
        payload = {
            "gate": "all",
            "event": "get",
            "camera": "camera1"
        }
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            data = response.json()
            available_slots = {}
            for key, value in data['data'].items():
                if key.endswith('_left'):
                    zone_name = key.replace('_left', '')
                    available_slots[zone_name] = value
            return available_slots
        else:
            print(f"Failed to get available slots. Status Code: {response.status_code}")
            return None
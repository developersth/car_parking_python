import requests

# Base URL of the server
BASE_URL = 'http://127.0.0.1:5000'

def get_available_slots():
    url = f'{BASE_URL}/event'
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

if __name__ == '__main__':
    available_slots = get_available_slots()
    if available_slots:
        print("Available Slots:")
        for zone, slots in available_slots.items():
            print(f"{zone}: {slots}")
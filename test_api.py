import requests, time

# Base URL of the server
BASE_URL = 'http://127.0.0.1:5000'

def test_event(gate, event, camera):
    url = f'{BASE_URL}/event'
    payload = {
        "gate": gate,
        "event": event,
        "camera": camera
    }
    response = requests.post(url, json=payload)
    print(f"Gate: {gate}, Event: {event}")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    print("-" * 40)

if __name__ == '__main__':
    gates = ['lab', 'a', 'b']
    events = ['out']
    cameras = ['camera1', 'camera2', 'camera3', 'camera4']

    for gate in gates:
        for event in events:
            camera = cameras[gates.index(gate)]  # Assign a unique camera for each gate
            test_event(gate, event, camera)
            k=input("press any key...")
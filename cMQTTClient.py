import paho.mqtt.client as mqtt
import time

class MQTTClient:
    def __init__(self, broker_address, port=1883, username=None, password=None):
        self.broker_address = broker_address
        self.port = int(port)
        self.username = username
        self.password = password
        self.client = mqtt.Client()

        # Set username and password if provided
        if username and password:
            self.client.username_pw_set(username, password)
        
        # Bind event callbacks
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        
        # Connection status
        self.connected = False

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("Connected successfully")
            self.connected = True
        else:
            print("Connection failed with code", rc)
            self.connected = False

    def on_disconnect(self, client, userdata, rc):
        print("Disconnected with code", rc)
        self.connected = False
        # Attempt to reconnect after disconnection
        self.reconnect()

    def connect(self):
        try:
            self.client.connect(self.broker_address, self.port)
            self.client.loop_start()
        except Exception as e:
            print(f"Failed to connect to {self.broker_address}: {e}")
            self.connected = False

    def reconnect(self):
        print("Attempting to reconnect...")
        while not self.connected:
            try:
                self.client.reconnect()
                time.sleep(1)  # Wait before retrying
            except Exception as e:
                print(f"Reconnect attempt failed: {e}")
                time.sleep(5)  # Longer wait after a failed reconnect

    def publish(self, topic, message, qos=0):
        # Check connection status and attempt reconnection if not connected
        if not self.connected:
            print("Not connected to MQTT broker, trying to reconnect...")
            self.reconnect()
        
        # Try publishing the message
        try:
            result = self.client.publish(topic, message, qos=qos)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"Message published to topic {topic}")
            else:
                print(f"Failed to publish message to topic {topic} (return code: {result.rc})")
        except Exception as e:
            print(f"Error publishing message: {e}")
            self.connected = False  # Mark disconnected on failure and try to reconnect
            self.reconnect()

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

import logging
import time
from datetime import datetime
from cParkingLotClient import ParkingLotClient
from cModbusLED import ModbusClient, ModbusLED
from cDeviceStatusUpdater import DeviceStatusUpdater
import os
import inspect
import requests
import threading
# Setup logging
log_directory = "C:/car_parking_logs"
os.makedirs(log_directory, exist_ok=True)  # Ensure the log directory exists
log_file = os.path.join(log_directory, "parking_lot_led_app_log.txt")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
    handlers=[
        logging.FileHandler(log_file),  # Log to file
        logging.StreamHandler()        # Log to console
    ]
)

brightness_schedule = {
    "05:00": {"default": 3},                            #Description:   Brightness Scoreboard 1, 2, 3 = 4
    "06:00": {"default": 5},                            #Description:   Brightness Scoreboard 1, 2, 3 = 6  
    "07:00": {"192.168.1.72": 5, "default": 7},         #Description:   Brightness Scoreboard 1, 2 = 8      | Brightness Scoreboard 3 = 6
    "12:00": {"default": 7},                            #Description:   Brightness Scoreboard 1, 2, 3 = 8  
    "13:00": {"192.168.1.72": 7, "default": 5},         #Description:   Brightness Scoreboard 1, 2 = 6      | Brightness Scoreboard 3 = 8
    "18:00": {"default": 5},                            #Description:   Brightness Scoreboard 1, 2, 3 = 6  
    "19:00": {"default": 3},                            #Description:   Brightness Scoreboard 1, 2, 3 = 4  
    "22:00": {"default": 1},                            #Description:   Brightness Scoreboard 1, 2, 3 = 2  
}

last_checked_time = None

def log_with_context(message, level=logging.INFO):
    """Helper function to log with file name and line number."""
    frame = inspect.currentframe().f_back
    filename = os.path.basename(frame.f_code.co_filename)
    line_number = frame.f_lineno
    log_message = f"{filename}:{line_number} - {message}"
    if level == logging.DEBUG:
        logging.debug(log_message)
    elif level == logging.INFO:
        logging.info(log_message)
    elif level == logging.WARNING:
        logging.warning(log_message)
    elif level == logging.ERROR:
        logging.error(log_message)
    elif level == logging.CRITICAL:
        logging.critical(log_message)

class ParkingLotLEDApp:
    """Main application class to run Parking Lot client operations and display on LED."""
    server_url = "http://localhost:5000"  # Replace with actual server URL
    updater = DeviceStatusUpdater(server_url)

    def __init__(self, base_url, modbus_hosts=None, modbus_port=502):
        if modbus_hosts is None:
            modbus_hosts = ["192.168.1.61", "192.168.1.71", "192.168.1.72"]  # Default IPs
        self.modbus_hosts = modbus_hosts
        self.modbus_port = modbus_port
        self.parking_lot_client = ParkingLotClient(base_url)
        log_with_context(f"Initialized ParkingLotLEDApp with base URL: {base_url}")
        self.init_modbus()

        # Initialize the thread for monitoring led status
        self.monitor_thread = threading.Thread(target=self.update_device_status)
        self.monitor_thread.daemon = True  # Daemon thread will exit when the main program exits
      

    def create_modbus_client(self, host):
        client = ModbusClient(host=host, port=self.modbus_port)
        if not client.connect():
            log_with_context(f"Warning Failed to connect to {host}, retrying in 5 seconds...", logging.warning)
            time.sleep(5)
            client.connect()
        return client

    def init_modbus(self):
        self.modbus_clients = []
        self.led_displays = []
        
        # Initialize Modbus clients and LED displays for each host
        for host in self.modbus_hosts:
            try:
                modbus_client = self.create_modbus_client(host)

                self.modbus_clients.append(modbus_client)
                self.led_displays.append(ModbusLED(modbus_client))
            except Exception as e:
                log_with_context(f"Error connecting to Modbus client at {host}: {e}", logging.ERROR)
                continue

    def update_device_status(self):
        """Check the connection status of all Modbus devices and update the server."""
        while True:
            for i, host in enumerate(self.modbus_hosts):
                device = "led1" if host == "192.168.1.61" else "led2" if host == "192.168.1.71" else "led3"
                status = "online" if self.modbus_clients[i].client.connected else "offline"

                try:
                    response = self.updater.send_status(device, status)
                    time.sleep(0.5) # Wait for 1 minute before sending the next status update
                    if "error" in response:
                        log_with_context(f"Failed to update status for {device} ({host}): {response['error']}", logging.ERROR)
                    #else:
                    # log_with_context(f"Updated status for {device} ({host}): {status}")
                except Exception as e:
                    log_with_context(f"Error updating device status for {device}: {e}", logging.ERROR)

            time.sleep(60)  # Check status every 10 seconds

    def update_brightness(self):
        global last_checked_time
        current_time = datetime.now().strftime('%H:%M')

        if current_time in brightness_schedule and last_checked_time != current_time:

            for led in self.led_displays:
                led_ip = led.client.host
                brightness = brightness_schedule[current_time].get(led_ip, brightness_schedule[current_time].get("default", 0))

                try:

                    if led.client.connect():
                        led.set_brightness(brightness)
                        time.sleep(0.2)
                        log_with_context(f"Set brightness {brightness} for LED at {led_ip}")
                    else:
                        log_with_context(f"Reconnecting to {led_ip}", logging.WARNING)
                        new_client = self.create_modbus_client(led_ip)
                        led.client= new_client
                        led.set_brightness(brightness)
                        time.sleep(0.2)

                except Exception as e:
                    log_with_context(f"Error updating brightness for {led_ip}: {e}", logging.ERROR)  # Fixed missing log message

            last_checked_time = current_time



    def run(self):
        """Main function to run Parking Lot client operations and display on LED."""
        retry_count = 0
        max_retries = 240 # 1hr
        retry_delay = 15  # seconds
        # Get the count of items in self.led_displays

        # Log the count
        self.monitor_thread.start()
        try:
            while True:
                try:
                 
                    self.update_brightness()
                    # Fetch available slots from the server
                    available_slots = self.parking_lot_client.get_available_slots()
                    if available_slots:
                        log_with_context(f"Available Slots: {available_slots}")

                        for gate, slots in available_slots.items():
                            if 'mg' in gate:
                                continue
                            gate = gate.replace("current_", "")
                            if slots <= 3:
                                slots = 'Full'

                            # Write to each LED display
                            for led in self.led_displays:
                                try:
                                    led.write(gate.capitalize(), slots)
                                    time.sleep(0.2)
                                except Exception as e:
                                    log_with_context(f"Error writing to LED display: {e}", logging.ERROR)
                                    log_with_context("Modbus Client: Closing...")
                                    self.close()
                                    log_with_context("Modbus Client: Closed")
                                    time.sleep(1.0)
                                    log_with_context("Modbus Client: Initializing...")
                                    self.init_modbus()
                                    log_with_context("Modbus Client: Initialized")
                                    break

                    else:
                        log_with_context("Failed to get available slots.", logging.WARNING)

                    # Reset retry count on successful fetch
                    retry_count = 0

                except requests.exceptions.ConnectionError as e:
                    # Handle connection errors
                    retry_count += 1
                    log_with_context(f"Connection error: {e}. Retrying in {retry_delay} seconds (Attempt {retry_count}/{max_retries})", logging.ERROR)
                    if retry_count >= max_retries:
                        log_with_context("Max retries reached. Exiting application.", logging.CRITICAL)
                        break
                    time.sleep(retry_delay)

                except Exception as e:
                    # Handle other unexpected errors
                    log_with_context(f"Unexpected error: {e}", logging.ERROR)
                    break

                time.sleep(1.0)

        except KeyboardInterrupt:
            log_with_context("\nExiting loop.")

    def close(self):
        for client in self.modbus_clients:
            try:
                client.close()
                log_with_context(f"Closed Modbus client: {client.host}")
            except Exception as e:
                log_with_context(f"Error closing Modbus client: {e}", logging.ERROR)

if __name__ == "__main__":
    base_url = "http://127.0.0.1:5000"  # Replace with your actual server URL
    app = ParkingLotLEDApp(base_url)
    log_with_context("Starting ParkingLotLEDApp")
    app.run()
    app.close()
    log_with_context("ParkingLotLEDApp stopped")
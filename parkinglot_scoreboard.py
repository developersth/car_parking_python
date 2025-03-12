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
        self.monitor_thread.start()
      
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

            
    # def create_modbus_client(self, host):
    #     client = ModbusClient(host=host, port=self.modbus_port)
    #     if not client.connect():
    #         log_with_context(f"Failed to connect to {host}, retrying in 5 seconds...", logging.WARNING)
    #         time.sleep(5)
    #         if not client.connect():
    #             log_with_context(f"Still unable to connect to {host}, will skip this client.", logging.ERROR)
    #     return client
    
    def reconnect_modbus_client(self, host):
        """Reconnect Modbus client if disconnected."""
        log_with_context(f"Reconnecting to {host}...", logging.WARNING)
        new_client = self.create_modbus_client(host)

        if new_client and new_client.connect():
            log_with_context(f"Reconnected to {host} successfully.", logging.INFO)
            return new_client
        else:
            log_with_context(f"Failed to reconnect to {host}.", logging.ERROR)
            return None

    # def update_device_status(self):
    #     """Check the connection status of all Modbus devices and reconnect if necessary."""
    #     device_map = {
    #         "192.168.1.61": "led1",
    #         "192.168.1.71": "led2",
    #         "192.168.1.72": "led3"
    #     }

    #     while True:
    #         time.sleep(10)
    #         for i, host in enumerate(self.modbus_hosts):
    #             status = "offline"
    #             device = device_map.get(host, None)

    #             modbus_client = self.modbus_clients[i] if i < len(self.modbus_clients) else None

    #             if modbus_client and modbus_client.client:
    #                 status = "online" if modbus_client.client.connected else "offline"

    #             # ถ้า offline ให้ลอง reconnect
    #             if status == "offline":
    #                 log_with_context(f"Device {device} ({host}) is offline. Attempting to reconnect...", logging.WARNING)
    #                 new_client = self.reconnect_modbus_client(host)
    #                 if new_client:
    #                     self.modbus_clients[i] = new_client  # อัปเดตเป็น client ใหม่
    #                     status = "online"

    #             # อัปเดตสถานะไปยัง server
    #             if device:
    #                 try:
    #                     response = self.updater.send_status(device, status)
    #                     if response and "error" in response:
    #                         log_with_context(f"Failed to update status for {device} ({host}): {response['error']}", logging.ERROR)
    #                 except Exception as e:
    #                     log_with_context(f"Error updating device status for {device}: {e}", logging.ERROR)

    #             time.sleep(0.5)

    def update_device_status(self):
        """Check and update device status. Attempt reconnection if a device is offline."""
        while True:
            for i, host in enumerate(self.modbus_hosts):
                device = f"led{i+1}"
                client = self.modbus_clients[i]

                if client is None or not client.client.connected:
                    log_with_context(f"{device} ({host}) is offline. Attempting reconnect...", logging.WARNING)
                    new_client = self.create_modbus_client(host)
                    
                    if new_client:
                        self.modbus_clients[i] = new_client
                        log_with_context(f"Reconnected {device} ({host}).", logging.INFO)
                    else:
                        log_with_context(f"Failed to reconnect {device} ({host}).", logging.ERROR)
                        status = "offline"
                else:
                    status = "online"

                try:
                    response = self.updater.send_status(device, status)
                    time.sleep(0.5)
                    if "error" in response:
                        log_with_context(f"Failed to update status for {device} ({host}): {response['error']}", logging.ERROR)
                except Exception as e:
                    log_with_context(f"Error updating device status for {device}: {e}", logging.ERROR)

            time.sleep(30)

      
    # def update_brightness(self):
    #     global last_checked_time
    #     current_time = datetime.now().strftime('%H:%M')

    #     if current_time in brightness_schedule and last_checked_time != current_time:

    #         for led in self.led_displays:
    #             led_ip = led.client.host
    #             brightness = brightness_schedule[current_time].get(led_ip, brightness_schedule[current_time].get("default", 0))

    #             try:

    #                 if led.client.connect():
    #                     led.set_brightness(brightness)
    #                     time.sleep(0.2)
    #                     log_with_context(f"Set brightness {brightness} for LED at {led_ip}")
    #                 else:
    #                     log_with_context(f"Reconnecting to {led_ip}", logging.WARNING)
    #                     new_client = self.create_modbus_client(led_ip)
    #                     led.client= new_client
    #                     led.set_brightness(brightness)
    #                     time.sleep(0.2)

    #             except Exception as e:
    #                 log_with_context(f"Error updating brightness for {led_ip}: {e}", logging.ERROR)  # Fixed missing log message

    #         last_checked_time = current_time

    def update_brightness(self):
        global last_checked_time
        current_time = datetime.now().strftime('%H:%M')

        if current_time in brightness_schedule and last_checked_time != current_time:
            for led in self.led_displays:
                led_ip = led.client.host
                brightness = brightness_schedule[current_time].get(led_ip, brightness_schedule[current_time].get("default", 0))

                try:
                    if not led.is_connected:  # Check connection
                        log_with_context(f"Reconnecting to {led_ip}", logging.WARNING)
                        new_client = self.create_modbus_client(led_ip)
                        if new_client:
                            led.client = new_client
                            log_with_context(f"Reconnected to {led_ip}")
                        else:
                            log_with_context(f"Failed to reconnect to {led_ip}. Skipping brightness update.", logging.ERROR)
                            continue

                    led.set_brightness(brightness)
                    time.sleep(0.2)
                    log_with_context(f"Set brightness {brightness} for LED at {led_ip}")

                except Exception as e:
                    log_with_context(f"Error updating brightness for {led_ip}: {e}", logging.ERROR)

            last_checked_time = current_time



    def run(self):
        """Main function to run Parking Lot client operations and display on LED."""
        retry_count = 0
        max_retries = 240  # 1hr
        retry_delay = 15  # seconds

        try:
            while True:
                try:
                    time.sleep(0.5)
                    self.update_brightness()

                    available_slots = self.parking_lot_client.get_available_slots()
                    if available_slots:
                        log_with_context(f"Available Slots: {available_slots}")

                        for gate, slots in available_slots.items():
                            if 'mg' in gate:
                                continue
                            gate = gate.replace("current_", "")
                            if slots <= 5:
                                slots = 'Full'

                            # Write to each LED display
                            for i, led in enumerate(self.led_displays):
                                try:
                                    if led.is_connected():
                                        led.write(gate.capitalize(), slots)
                                        time.sleep(0.2)
                                    else:
                                        log_with_context(f"LED at {self.modbus_hosts[i]} disconnected, reconnecting...", logging.WARNING)
                                        new_client = self.reconnect_modbus_client(self.modbus_hosts[i])
                                        if new_client:
                                            self.modbus_clients[i] = new_client
                                            led.client = new_client
                                            led.write(gate.capitalize(), slots)
                                        else:
                                            log_with_context(f"Failed to reconnect LED at {self.modbus_hosts[i]}", logging.ERROR)

                                except Exception as e:
                                    log_with_context(f"Error writing to LED display: {e}", logging.ERROR)

                    else:
                        log_with_context("Failed to get available slots.", logging.WARNING)

                    retry_count = 0

                except requests.exceptions.ConnectionError as e:
                    retry_count += 1
                    log_with_context(f"Connection error: {e}. Retrying in {retry_delay} seconds (Attempt {retry_count}/{max_retries})", logging.ERROR)
                    if retry_count >= max_retries:
                        log_with_context("Max retries reached. Exiting application.", logging.CRITICAL)
                        break
                    time.sleep(retry_delay)

                except Exception as e:
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
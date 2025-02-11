import logging
import time
from cParkingLotClient import ParkingLotClient
from cModbusLED import ModbusClient, ModbusLED
import os
import inspect
import requests

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
    
    def __init__(self, base_url, modbus_hosts=None, modbus_port=502):
        if modbus_hosts is None:
            modbus_hosts = ["192.168.1.61", "192.168.1.71", "192.168.1.72"]  # Default IPs
        self.modbus_hosts = modbus_hosts
        self.modbus_port = modbus_port
        self.parking_lot_client = ParkingLotClient(base_url)
        log_with_context(f"Initialized ParkingLotLEDApp with base URL: {base_url}")
        self.init_modbus()

    def init_modbus(self):
        self.modbus_clients = []
        self.led_displays = []
        
        # Initialize Modbus clients and LED displays for each host
        for host in self.modbus_hosts:
            try:
                modbus_client = ModbusClient(host=host, port=self.modbus_port)
                modbus_client.connect()
                self.modbus_clients.append(modbus_client)
                self.led_displays.append(ModbusLED(modbus_client))
                log_with_context(f"Connected to Modbus Client at {host}")
            except Exception as e:
                log_with_context(f"Error connecting to Modbus client at {host}: {e}", logging.ERROR)
                continue

    def run(self):
        """Main function to run Parking Lot client operations and display on LED."""
        retry_count = 0
        max_retries = 240 # 1hr
        retry_delay = 15  # seconds

        try:
            while True:
                try:
                    # Fetch available slots from the server
                    available_slots = self.parking_lot_client.get_available_slots()
                    if available_slots:
                        log_with_context(f"Available Slots: {available_slots}")
                        for gate, slots in available_slots.items():
                            if 'mg' in gate:
                                continue
                            gate = gate.replace("current_", "")
                            if slots <= 3:
                                slots = 'FULL'
                            
                            # Write to each LED display
                            for led in self.led_displays:
                                try:
                                    led.write(gate.capitalize(), slots)
                                    log_with_context(f"Updated LED display for gate {gate} with slots: {slots}")
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
#!/usr/bin/env python3
"""Parking Lot Client Example to collect available slots and display on LED board."""

import logging
import time
from cParkingLotClient import ParkingLotClient
from cModbusLED import ModbusClient, ModbusLED

# Setup logging
_logger = logging.getLogger(__file__)
_logger.setLevel("DEBUG")

class ParkingLotLEDApp:
    """Main application class to run Parking Lot client operations and display on LED."""
    
    def __init__(self, base_url, modbus_host="192.168.1.61", modbus_port=502):
        self.modbus_host = modbus_host
        self.modbus_port = modbus_port
        self.parking_lot_client = ParkingLotClient(base_url)
        self.init_modbus()

    def init_modbus(self):
        self.modbus_client = ModbusClient(host=self.modbus_host, port=self.modbus_port)
        self.modbus_client.connect()
        self.led = ModbusLED(self.modbus_client)

    def run(self):
        """Main function to run Parking Lot client operations and display on LED."""
        try:
            while True:
                available_slots = self.parking_lot_client.get_available_slots()
                if available_slots:
                    print("Available Slots:", available_slots)
                    for gate, slots in available_slots.items():
                        if 'mg' in gate:
                            continue
                        gate = gate.replace("current_", "")
                        if slots<=0:
                            slots = 'FULL'
                        try:
                            self.led.write(gate.capitalize(), slots)
                        except Exception as e:
                            print(e)
                            print("Modbus Client: Closing...")
                            self.close()
                            print("Modbus Client: Closed")
                            time.sleep(1.0)
                            print("Modbus Client: Initial...")
                            self.init_modbus()
                            print("Modbus Client: Initialed")
                else:
                    print("Failed to get available slots.")
                time.sleep(1.0)
        except KeyboardInterrupt:
            print("\nExiting loop.")

    def close(self):
        self.modbus_client.close()

if __name__ == "__main__":
    base_url = "http://127.0.0.1:5000"  # Replace with your actual server URL
    app = ParkingLotLEDApp(base_url)
    app.run()
    app.close()
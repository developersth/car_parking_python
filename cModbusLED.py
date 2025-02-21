#!/usr/bin/env python3
"""Modbus TCP Client Example with IP address 192.168.1.244."""

import logging
from pymodbus.client import ModbusTcpClient
from pymodbus import ModbusException
import random
import time

# Setup logging
_logger = logging.getLogger(__file__)
_logger.setLevel("DEBUG")

class ModbusClient:
    """Class to handle Modbus TCP client operations."""
    
    # def __init__(self, host="192.168.1.61", port=502, timeout=2):
    #     """Initialize ModbusClient with connection parameters."""
    #     _logger.info("### Creating Modbus TCP client")
    #     self.client = ModbusTcpClient(host=host, port=port, framer="socket", timeout=timeout)

   
    # def connect(self):
    #     """Connect to the Modbus server."""
    #     if self.client.connect():
    #         _logger.info("Connected to Modbus server")
    #     else:
    #         _logger.error("Failed to connect to Modbus server")

    # def close(self):
    #     """Close the connection to the Modbus server."""
    #     self.client.close()
    #     _logger.info("### Connection closed")

    def __init__(self, host="192.168.1.61", port=502, timeout=2):
        """Initialize ModbusClient with connection parameters."""
        _logger.info("### Creating Modbus TCP client")
        self.host = host  # Store the host IP address as an attribute
        self.client = ModbusTcpClient(host, port=port, framer="socket", timeout=timeout)
   
    def connect(self):
        """Connect to the Modbus server."""
        if self.client.connect():
            _logger.info("Connected to Modbus server")
        else:
            _logger.error("Failed to connect to Modbus server")

    def close(self):
        """Close the connection to the Modbus server."""
        self.client.close()
        _logger.info("### Connection closed")

    def read_register_group(self, start, count):
        """Read a group of registers from the Modbus server."""
        try:
            rr = self.client.read_holding_registers(start, count, unit=1)
            if not rr.isError():
                return self.registers_to_text(rr.registers)
            else:
                _logger.error(f"Failed to read registers {start} to {start+count-1}: {rr}")
        except ModbusException as exc:
            _logger.error(f"Modbus exception occurred: {exc}")
            raise exc
        return None

    def write_register_group(self, start, data_str):
        """Write a string to a group of registers on the Modbus server."""
        if len(data_str) != 4:
            raise ValueError("Input string must be between 4 and 5 characters.")
        
        values = self.text_to_registers(data_str)

        try:
            response = self.client.write_registers(start, values, unit=1)
            if response.isError():
                _logger.error(f"Failed to write to registers {start} to {start+len(values)-1}")
            # else:
            #     _logger.info(f"Successfully wrote to registers {start} to {start+len(values)-1}")
        except ModbusException as exc:
            _logger.error(f"Modbus exception occurred while writing: {exc}")
            raise exc

    def registers_to_text(self, registers):
        """Convert a list of register values to ASCII text."""
        text = ""
        for reg in registers:
            hex_value = f"{reg:04X}"
            try:
                char_pair = bytes.fromhex(hex_value).decode('ascii')
                text += char_pair
            except ValueError:
                text += "?"
                print(f"Warning: Could not decode hex value {hex_value}")
        return text

    def text_to_registers(self, text):
        if text == 'UFLL':
            return [21830, 19532]
        
        registers = []
        for i in range(0, len(text), 2):
            char_pair = text[i:i+2].ljust(2, '\x00')
            registers.append(int.from_bytes(char_pair.encode('ascii'), byteorder='big'))
        return registers


class ModbusLED:
    """Class for Modbus LED operations, reading/writing groups as JSON data."""
    
    def __init__(self, client):
        """Initialize ModbusLED with an instance of ModbusClient."""
        self.client = client
        self.group_addr = {
            'A': (60, '', 3, 213, 214),
            'B': (70, '', 3, 216, 217),
            'Lab': (80, '', 3, 219, 220)
        }

    def read(self):
        """Read values for groups A, B, Lab, and Mg, returning data as JSON."""
        data = {}
        for key in self.group_addr:
            register_addr = self.group_addr[key][0]
            data[key] = self.client.read_register_group(register_addr, 2)

        for key in data:
            if data[key] and len(data[key]) == 4:
                data[key] = data[key][1] + data[key][0] + data[key][3] + data[key][2]
                data[key] = data[key].replace('\x00', '')
            else:
                data[key] = None

        return {
            'A': data['A'] if data['A'] else None,
            'B': data['B'] if data['B'] else None,
            'Lab': data['Lab'] if data['Lab'] else None,
        }

    def readInt(self):
        msg = self.read()
        for key in msg:
            msg[key] = int(msg[key].replace(self.group_addr[key][1], ''))
        return msg

    def write(self, group, value):
        """Write a decimal value to a specified group register."""

        digit = self.group_addr[group][2]
        register_addr = self.group_addr[group][0]
        register_label = self.group_addr[group][1]

        font_size = 4 
        color = 5 #
        if value == 'FULL':
            font_size = 3
            color = 0

        response = self.client.client.write_registers(self.group_addr[group][3], font_size, unit=1)
        if response.isError():
            # _logger.error(f"Failed to write to registers {start} to {start+len(values)-1}")
            _logger.error(f"Failed to write to registers.")
        response = self.client.client.write_registers(self.group_addr[group][4], color, unit=1)
        if response.isError():
            # _logger.error(f"Failed to write to registers {start} to {start+len(values)-1}")
            _logger.error(f"Failed to write to registers.")

        if value == 'FULL':
            self.client.write_register_group(register_addr, 'UFLL')
        else:
            value = str(value).zfill(digit)
            msg = value[1] + value[0] + '\x00' + value[2]
            self.client.write_register_group(register_addr, msg)

    def write_scoreboard1(self, group, value):
        """Write a decimal value to a specified group register."""

        digit = self.group_addr[group][2]
        register_addr = self.group_addr[group][0]
        register_label = self.group_addr[group][1]

        font_size = 1
        color = 1 #
        if value == 'FULL':
            font_size = 1
            color = 0

        response = self.client.client.write_registers(self.group_addr[group][3], font_size, unit=1)
        if response.isError():
            # _logger.error(f"Failed to write to registers {start} to {start+len(values)-1}")
            _logger.error(f"Failed to write to registers.")
        response = self.client.client.write_registers(self.group_addr[group][4], color, unit=1)
        if response.isError():
            # _logger.error(f"Failed to write to registers {start} to {start+len(values)-1}")
            _logger.error(f"Failed to write to registers.")

        if value == 'FULL':
            self.client.write_register_group(register_addr, 'UFLL')
        else:
            value = str(value).zfill(digit)
            msg = value[1] + value[0] + '\x00' + value[2]
            self.client.write_register_group(register_addr, msg)
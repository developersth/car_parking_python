#!/usr/bin/env python3
"""Modbus TCP Client Example with IP address 192.168.1.244."""

import logging
from pymodbus.client import ModbusTcpClient
from pymodbus import ModbusException
import random, time

# Setup logging
_logger = logging.getLogger(__file__)
_logger.setLevel("DEBUG")

class ModbusClient:
    """Class to handle Modbus TCP client operations."""
    
    def __init__(self, host="192.168.1.61", port=502, timeout=2):
        """Initialize ModbusClient with connection parameters."""
        _logger.info("### Creating Modbus TCP client")
        self.client = ModbusTcpClient(host=host, port=port, framer="socket", timeout=timeout)

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
                #print('rr: ', rr.registers)
                return self.registers_to_text(rr.registers)
            else:
                _logger.error(f"Failed to read registers {start} to {start+count-1}: {rr}")
        except ModbusException as exc:
            _logger.error(f"Modbus exception occurred: {exc}")
            raise exc
        return None

    def write_register_group(self, start, data_str):
        print([data_str, len(data_str)])
        """Write a string to a group of registers on the Modbus server."""
        if len(data_str) != 4:
            raise ValueError("Input string must be between 4 and 5 characters.")
        
        # Convert the string to a list of register values
        values = self.text_to_registers(data_str)
        #print('text_to_registers: ', values)
        #values = [21830, 19532]

        try:
            #print('start: ', start)
            #print('values: ', values)
            #values = [21830, 19532]
            #print('force: ', values)
            response = self.client.write_registers(start, values.copy(), unit=1)
            if response.isError():
                _logger.error(f"Failed to write to registers {start} to {start+len(values)-1}")
            else:
                _logger.info(f"Successfully wrote to registers {start} to {start+len(values)-1}")
        except ModbusException as exc:
            _logger.error(f"Modbus exception occurred while writing: {exc}")
            raise exc

    def registers_to_text(self, registers):
        """Convert a list of register values to ASCII text."""
        text = ""
        for reg in registers:
            # Convert each register (integer) to a hexadecimal string, padded to 4 characters
            hex_value = f"{reg:04X}"
            #print(hex_value)
            
            # Convert each pair of hex digits to a character
            try:
                char_pair = bytes.fromhex(hex_value).decode('ascii')
                text += char_pair
            except ValueError:
                # If the hex pair can't be converted, add placeholder or skip
                text += "?"
                print(f"Warning: Could not decode hex value {hex_value}")
                
        return text

    def text_to_registers(self, text):
        #print('text: ', text, ', len: ', len(text))
        if text == 'UFLL':
            #print('found: UFLL')
            registers = [21830, 19532]
            return registers
        """Convert a string to a list of register values."""
        registers = []
        # Convert each pair of characters into a 2-byte integer (register value)
        for i in range(0, len(text), 2):
            char_pair = text[i:i+2].ljust(2, '\x00')  # Pad if odd length
            registers.append(int.from_bytes(char_pair.encode('ascii'), byteorder='big'))
        return registers


class ModbusLED:
    """Class for Modbus LED operations, reading/writing groups as JSON data."""
    
    def __init__(self, client):
        """Initialize ModbusLED with an instance of ModbusClient."""
        self.client = client
        
        # (DigitAddr, Label, DigitNum, FontAddr, ColorAddr)
        #self.group_addr = {'A': (60, 'A', 3), 'B': (70, 'B', 3), 'Lab': (80, 'LB', 2), 'Mg': (90, 'MG', 2)}
        self.group_addr = {'A': (60, '', 3, 213, 214), 'B': (70, '', 3, 216, 217), 'Lab': (80, '', 3, 219, 220)}

    def read(self):
        """Read values for groups A, B, Lab, and Mg, returning data as JSON."""
        data = {}
        for key in self.group_addr:
            register_addr = self.group_addr[key][0]
            data[key] = self.client.read_register_group(register_addr, 2)

        #print(data)
        # Apply index reordering for each key if data is valid
        for key in data:
            #print(len(data[key]))
            if data[key] and len(data[key]) == 4:
                data[key] = data[key][1] + data[key][0] + data[key][3] + data[key][2]
                data[key] = data[key].replace('\x00', '')
            else:
                data[key] = None  # Set to None if data is invalid or missing

        # Convert register lists to single decimal numbers for JSON output
        return {
            'A': data['A'] if data['A'] else None,
            'B': data['B'] if data['B'] else None,
            'Lab': data['Lab'] if data['Lab'] else None,
        }

    def readInt(self):
        msg = self.read()
        #print(msg)
        for key in msg:
            #print(key)
            #print(msg[key])
            #print(self.group_addr[key])
            msg[key] = int(msg[key].replace(self.group_addr[key][1], ''))
        return msg

    def write(self, group, value):
        """Write a decimal value to a specified group register."""
        digit = self.group_addr[group][2]
        register_addr = self.group_addr[group][0]
        register_label = self.group_addr[group][1]

        font_size = 4
        color = 1
        if value == 'FULL':
            font_size = 3
            color = 0

        response = self.client.client.write_registers(self.group_addr[group][3], font_size, unit=1)
        if response.isError():
            _logger.error(f"Failed to write to registers {start} to {start+len(values)-1}")
        response = self.client.client.write_registers(self.group_addr[group][4], color, unit=1)
        if response.isError():
            _logger.error(f"Failed to write to registers {start} to {start+len(values)-1}")

        if value == 'FULL':
            self.client.write_register_group(register_addr, 'UFLL')
            if response.isError():
                _logger.error(f"Failed to write to registers {start} to {start+len(values)-1}")
        else:
            value = str(value).zfill(digit)
            #print([value, len(value)])
            #msg = register_label + value
            #print([msg, len(msg)])
            #msg = msg[1] + msg[0] + msg[3] + msg[2]
            msg = value[1] + value[0] + '\x00' + value[2]
            #print([msg, len(msg)])

            self.client.write_register_group(register_addr, msg)
        '''
        except Exception as e:
            _logger.error(f"Invalid group '{group}' specified for write operation.")
        '''

def main():
    """Main function to run Modbus client operations."""
    cli = ModbusClient()
    cli.connect()

    led = ModbusLED(cli)

    try:
        while True:
            maxNum = [85, 123, 110]
            data = ['FULL', 0, 0]
            random.shuffle(data)
            for i in range(len(data)):
                if data[i] != 'FULL':
                    data[i] = random.randint(0, maxNum[i])

            #writeData = {'A': random.randint(0, 200), 'B': random.randint(0, 200), 'Lab': random.randint(0, 99), 'Mg': random.randint(0, 99)}
            writeData = {'A': data[0], 'B': data[1], 'Lab': data[2]}
            #writeData = {'A': 123, 'B': 456, 'Lab': 789}

            # Write example values to specific groups
            for key in writeData:
                print(['for key in writeData:', writeData[key], key])
                led.write(key, writeData[key])

            # Read and display all group data as JSON
            #readData = led.readInt()

            #print("read :", readData)
            print("write:", writeData)
            time.sleep(5.0)
    except KeyboardInterrupt:
        print("\nExiting loop.")
    

    cli.close()

if __name__ == "__main__":
    main()
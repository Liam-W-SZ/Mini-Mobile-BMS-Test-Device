import serial
import time
import json 

K2C = 273.1

class BMSCommunicator:
    def __init__(self, port='/dev/ttyUSB0', baudrate=19200):
        self.serial = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=0.5  # Reduced from 1 to 0.5 seconds
        )
        
    def send_command(self, command):
        self.serial.write(command)        
        # First read 3 bytes to get the response length
        header = self.serial.read(3)
        if len(header) < 3:
            return b''
            
        # Calculate total remaining bytes (including CRC)
        data_length = header[2]
        remaining_bytes = data_length + 2  # Add 2 for CRC bytes
        
        # Read the rest of the response
        response = header + self.serial.read(remaining_bytes)
        return response
    
    def calculate_crc(self, data):
        """Calculate CRC for the given data using CRC-16-CCITT."""
        crc = 0xFFFF  # Initial value
        for byte in data:
            crc ^= byte  # XOR byte into least significant byte of crc
            for _ in range(8):  # Process each bit
                if crc & 0x0001:  # If the LSB is set
                    crc >>= 1  # Shift right
                    crc ^= 0xA001  # XOR with polynomial
                else:
                    crc >>= 1  # Just shift right
        return crc
    
    def check_crc(self, data):
        """Check that the received data has a valid CRC"""
        # Ensure the received data is long enough to contain a CRC
        if len(data) < 2:
            return False  # Return False if data is invalid

        crc = self.calculate_crc(data[:-2])

        received_crc = int.from_bytes(data[-2:], byteorder='little')

        # print(crc == received_crc)
        return crc == received_crc
    
    def get_pack_info(self):
        """Get PIA, PIB, and PIC information"""
        try:
            
            info_cmd = bytes.fromhex('00 04 17 00 00 33')  # Pack#0Parameters【Serial battery number】 (CRC -> B4 7A)
            crc_info = self.calculate_crc(info_cmd)  # Calculate CRC for Device
            info_cmd += crc_info.to_bytes(2, byteorder='little')  # Append CRC to command
            #print(bytes.hex(info_cmd))
            
            # Commands for PIA, PIB, PIC
            pia_cmd = bytes.fromhex('00 04 10 00 00 12')  # command for PIA (CRC-> 75 16)
            crc_pia = self.calculate_crc(pia_cmd)  # Calculate CRC for PIA
            pia_cmd += crc_pia.to_bytes(2, byteorder='little')  # Append CRC to command
            #print(bytes.hex(pia_cmd))
            
            pib_cmd = bytes.fromhex('00 04 11 00 00 1A')  # command for PIB (CRC -> 75 2C)
            crc_pib = self.calculate_crc(pib_cmd)  # Calculate CRC for PIB
            pib_cmd += crc_pib.to_bytes(2, byteorder='little')  # Append CRC to command
            #print(bytes.hex(pib_cmd))
            
            pic_cmd = bytes.fromhex('00 01 12 00 00 90')  # command for PIC
            crc_pic = self.calculate_crc(pic_cmd)
            pic_cmd += crc_pic.to_bytes(2, byteorder='little')

            alarm_cmd = bytes.fromhex('00 01 14 00 00 50')  # command for Alarms
            crc_alarm = self.calculate_crc(alarm_cmd)          
            alarm_cmd += crc_alarm.to_bytes(2, byteorder='little')
            #print(f'Alarms data: {bytes.hex(alarm_cmd)}')

            func_switch_param_cmd = bytes.fromhex('00 01 14 00 00 50') # command for Function Switch Param
            crc_func = self.calculate_crc(func_switch_param_cmd)  # Calculate CRC for Function Switch Param
            func_switch_param_cmd += crc_func.to_bytes(2, byteorder='little')  # Append CRC to command
            #print(f'Function Switch Param data: {bytes.hex(func_switch_param_cmd)}')

            basic_param_cmd = bytes.fromhex('00 04 13 00 00 67')  # command for Basic Param
            crc_basic_param = self.calculate_crc(basic_param_cmd)
            basic_param_cmd += crc_basic_param.to_bytes(2, byteorder='little')
            #print(f'Basic Param data: {bytes.hex(basic_param_cmd)}')          


            # Get responses
            info_response = b''
            while not self.check_crc(info_response):
                info_response = self.send_command(info_cmd)
            #print('INFO --> DONE')
            
            #print(info_response.hex())            
            pia_response = b''
            while not self.check_crc(pia_response):
                pia_response = self.send_command(pia_cmd)
            #print('PIA --> DONE')
            
            #print(pia_response.hex())
            
            pib_response = b''    
            while not self.check_crc(pib_response):
                pib_response = self.send_command(pib_cmd)
            #print('PIB --> DONE')
            
            #print(pib_response.hex())
            
            pic_response = b''
            while not self.check_crc(pic_response):   
                pic_response = self.send_command(pic_cmd)
            #print('PIC --> DONE')
            
            #print(pic_response.hex())
            alarm_response = b''
            while not self.check_crc(alarm_response):   
                alarm_response = self.send_command(alarm_cmd)
            #print('ALARM --> DONE')            
            #print(alarm_response.hex())

            func_switch_param_response = b''
            while not self.check_crc(func_switch_param_response):
                func_switch_param_response = self.send_command(func_switch_param_cmd)
            #print('FUNCTION SWITCH PARAM --> DONE')
            #print(func_switch_param_response.hex())

            basic_param_response = b''
            while not self.check_crc(basic_param_response):
                basic_param_response = self.send_command(basic_param_cmd)
            #print('BASIC PARAM --> DONE')
            #print(basic_param_response.hex())

            # Parse responses
            pack_info = {
                'Acquire Device Manufacture Info' : self.parse_device_info(info_response),
                'PIA': self.parse_pia(pia_response),
                'PIB': self.parse_pib(pib_response),
                'PIC': self.parse_pic(pic_response),
                'Alarms' : self.parse_alarm(alarm_response),
                'Function Switch Param': self.parse_func_switch_param(func_switch_param_response),
                'Basic Param': self.parse_basic_param(basic_param_response)
            }
            
            # print(pack_info)
            # Save the parsed data to a JSON file
            self.save_to_json(pack_info, 'pack_info.json')
            
            return pack_info
            
        except Exception as e:
            print(f"Error communicating with BMS: {e}")
            return None
    
    def save_to_json(self, data, filename):
        """Save the given data to a JSON file in the specified directory."""
        import os
        try:
            data_folder = os.path.join(os.path.dirname(__file__), 'data')
            if not os.path.exists(data_folder):
                os.makedirs(data_folder)
            with open(os.path.join(data_folder, filename), 'w') as json_file:
                json.dump(data, json_file, indent=4)
            #print(f"✓ Data saved to {data_folder}/{filename}")
        except Exception as e:
            print(f"✗ Error saving data to JSON: {e}")
    
    def parse_pia(self, response):
        """Parse the PIA response from the BMS."""
        response = response[2:]
        
        # Extracting data based on the provided structure
        pack_voltage = int.from_bytes(response[1:3], byteorder='big') * 0.01  # 10mV
        current = int.from_bytes(response[3:5], byteorder='big', signed=True) * 0.01  # 10mA
        remaining_capacity = int.from_bytes(response[5:7], byteorder='big') * 0.01  # 10mAH
        total_capacity = int.from_bytes(response[7:9], byteorder='big') * 0.01  # 10mAH
        total_discharge_capacity = int.from_bytes(response[9:11], byteorder='big') * 1.0  # 10AH
        soc = int.from_bytes(response[11:13], byteorder='big') * 0.1  # 0.1%
        soh = int.from_bytes(response[13:15], byteorder='big') * 0.1  # 0.1%
        cycle = int.from_bytes(response[15:17], byteorder='big')  # 1
        avg_cell_voltage = int.from_bytes(response[17:19], byteorder='big') * 0.001  # 1mV
        avg_cell_temperature = (int.from_bytes(response[19:21], byteorder='big') * 0.1) - K2C  # 0.1K
        max_cell_voltage = int.from_bytes(response[21:23], byteorder='big') * 0.001  # 1mV
        min_cell_voltage = int.from_bytes(response[23:25], byteorder='big') * 0.001  # 1mV
        max_cell_temperature = (int.from_bytes(response[25:27], byteorder='big') * 0.1) - K2C  # 0.1K
        min_cell_temperature = (int.from_bytes(response[27:29], byteorder='big') * 0.1) - K2C  # 0.1K
        max_discharge_current = int.from_bytes(response[29:31], byteorder='big')  # 1A
        max_charge_current = int.from_bytes(response[31:33], byteorder='big')  # 1A
        # print(type(avg_cell_temperature))
        # print(round(avg_cell_temperature, 3))

        # Return parsed data as a dictionary
        return {
            'Pack Voltage': round(pack_voltage, 3),
            #'Current': round(current, 3),
            #'Remaining Capacity': round(remaining_capacity, 3),
            #'Total Capacity': round(total_capacity, 3),
            #'Total Discharge Capacity': round(total_discharge_capacity, 3),
            'SOC': round(soc, 3),
            #'SOH': round(soh, 3),
            #'Cycle': round(cycle, 3),
            'Average Cell Voltage': round(avg_cell_voltage, 3),
            #'Average Cell Temperature': round(avg_cell_temperature, 3),
            'Max Cell Voltage': round(max_cell_voltage, 3),
            'Min Cell Voltage': round(min_cell_voltage, 3),
            #'Max Cell Temperature': round(max_cell_temperature, 3),
            #'Min Cell Temperature': round(min_cell_temperature, 3),
            #'Max Discharge Current': round(max_discharge_current, 3),
            'Max Charge Current': round(max_charge_current, 3),
            #'Raw Response': response.hex()  # Include raw response for debugging
        }
    
    def parse_pib(self, response):
        """Parse the PIB response from the BMS."""
        response = response[2:]

        # Extracting cell voltages (16 cells)
        cell_voltages = {}
        for i in range(16):
            cell_voltage = int.from_bytes(response[2 * i + 1:2 * i + 3], byteorder='big') * 0.001  # 1mV
            cell_voltages[f'Cell {i + 1} Voltage'] = round(cell_voltage,3)

        # Extracting cell temperatures (4 cells)
        cell_temperatures = {}
        for i in range(4):
            cell_temperature = (int.from_bytes(response[33 + 2 * i:33 + 2 * i + 2], byteorder='big') * 0.1) - K2C  # Kelvin to Celcuis
            cell_temperatures[f'Cell Temperature {i + 1}'] = round(cell_temperature,3)

        # Extracting environment and power temperatures
        environment_temperature = (int.from_bytes(response[41:43], byteorder='big') * 0.1) - K2C  # 0.1K
        power_temperature = (int.from_bytes(response[43:45], byteorder='big') * 0.1) - K2C  # 0.1K

        # Return parsed data as a dictionary
        return {
            **cell_voltages,
            **cell_temperatures,
            'Environment Temperature': round(environment_temperature, 3),
            'Power Temperature': round(power_temperature, 3),
            #'Raw Response': response.hex()  # Include raw response for debugging
        }
    
    def parse_pic(self, response):
        """Parse the PIC response from the BMS."""

        # Extracting data based on the provided structure
        pic_data = {
            'Cell 08-01 Voltage Low Alarm State': response[3] & 0xFF,  # 8 bits
            'Cell 16-09 Voltage Low Alarm State': response[4] & 0xFF,  # 8 bits
            'Cell 08-01 Voltage High Alarm State': response[5] & 0xFF,  # 8 bits
            'Cell 16-09 Voltage High Alarm State': response[6] & 0xFF,  # 8 bits
            'Cell 08-01 Temperature Low Alarm State': response[7] & 0xFF,  # 8 bits
            'Cell 16-09 Temperature Low Alarm State': response[8] & 0xFF,  # 8 bits
            'Cell 08-01 Equalization Event Code': response[9] & 0xFF,  # 8 bits
            'Cell 16-09 Equalization Event Code': response[10] & 0xFF,  # 8 bits
            'System State Code': response[11] & 0xFF,  # 8 bits
            'Voltage Event Code': response[12] & 0xFF,  # 8 bits
            'Cells Temperature Event Code': response[13] & 0xFF,  # 8 bits
            'Environment and Power Temperature Event Code': response[14] & 0xFF,  # 8 bits
            'Current Event Code 1': response[15] & 0xFF,  # 8 bits
            'Current Event Code 2': response[16] & 0xFF,  # 8 bits
            'Residual Capacity Code': response[17] & 0xFF,  # 8 bits
            'FET Event Code': response[18] & 0xFF,  # 8 bits
            'Battery Equalization State Code': response[19] & 0xFF,  # 8 bits
            'Hard Fault Event Code': response[20] & 0xFF,  # 8 bits
            #'Raw Response': response.hex()  # Include raw response for debugging
        }
        
        return pic_data

    def parse_alarm(self, response):
        """Parse the Alarms response from the BMS."""

        # Extracting event codes from the response based on the provided structure
        alarm_data = {
            'Voltage Alarms 1': response[3],  # 8 bits, byte at index 11
            'Temperature Alarms': response[4],  # 8 bits, byte at index 12
            'Environment Alarms': response[5], # 8 bits, byte at index 13
            'Voltage Alarms 2': response[6],  # 8 bits, byte at index 14
            'Current Alarms 1': response[7],  # 8 bits, byte at index 15
            'Current Alarms 2': response[8],  # 8 bits, byte at index 16
            'Capacity and other Alarms': response[9],  # 8 bits, byte at index 17
            'Equalization Alarms': response[10],  # 8 bits, byte at index 18
            'Indicator Alarms': response[11],  # 8 bits, byte at index 19
            'Hard fault Alarms': response[12],  # 8 bits, byte at index 20
            
        }
        #print(f'{alarm_data}')
        return alarm_data
  
    def parse_func_switch_param(self, response):
        func_switch_param_data = {

            #fine Voltage Alarms 1
            'Cell high voltage alarm': ((response[3] >> 0) & 1),
            'Cell over voltage protection': ((response[3] >> 1) & 1),
            'Cell low voltage alarm': ((response[3] >> 2) & 1),
            'Cell under voltage protection': ((response[3] >> 3) & 1),
            'Battery high voltage alarm': ((response[3] >> 4) & 1),
            'Battery over voltage protection': ((response[3] >> 5) & 1),
            'Battery low voltage alarm': ((response[3] >> 6) & 1),
            'Battery under voltage protection': ((response[3] >> 7) & 1),

            #fine Temperature Alarms
            'Charge high temperature alarm': ((response[4] >> 0) & 1),
            'Charge over temperature protection': ((response[4] >> 1) & 1),
            'Charge low temperature alarm': ((response[4] >> 2) & 1),
            'Charge under temperature protection': ((response[4] >> 3) & 1),
            'Discharge high temperature alarm': ((response[4] >> 4) & 1),
            'Discharge over temperature protection': ((response[4] >> 5) & 1),
            'Discharge low temperature alarm': ((response[4] >> 6) & 1),
            'Discharge under temperature protection': ((response[4] >> 7) & 1),
            
            #fine Environment Alarms            
            'High ambient temperature alarm': ((response[5] >> 0) & 1),
            'Over ambient temperature protection': ((response[5] >> 1) & 1),
            'Low ambient temperature alarm': ((response[5] >> 2) & 1),
            'Under ambient temperature protection': ((response[5] >> 3) & 1),
            'Power high temperature alarm': ((response[5] >> 4) & 1),
            'Power over temperature protection': ((response[5] >> 5) & 1),
            'Cell temperature low heating': ((response[5] >> 6) & 1),
            'Cell voltage Fault (Reserved)': ((response[5] >> 7) & 1),

            #fine Voltage Alarms 2
            'Focs Output': ((response[6] >> 0) & 1),
            'Heat dissipation turned on': ((response[6] >> 1) & 1),
            'CapLeds idle display': ((response[6] >> 2) & 1),
            'Reserved 1 (Voltage Alarms 2)': ((response[6] >> 3) & 1),
            'Reserved 2 (Voltage Alarms 2)': ((response[6] >> 4) & 1),
            'Reserved 3 (Voltage Alarms 2)': ((response[6] >> 5) & 1),
            'Reserved 4 (Voltage Alarms 2)': ((response[6] >> 6) & 1),
            'Reserved 5 (Voltage Alarms 2)': ((response[6] >> 7) & 1),

            #Current Alarms 1
            'Charge current alarm': ((response[7] >> 0) & 1),
            'Charge over current protection': ((response[7] >> 1) & 1),
            'Secondary charge over current protection': ((response[7] >> 2) & 1),
            'Discharge current alarm': ((response[7] >> 3) & 1),
            'Discharge over current protection': ((response[7] >> 4) & 1),
            'Secondary discharge over current protection': ((response[7] >> 5) & 1),
            'Output short-circuit protection': ((response[7] >> 6) & 1),
            'Reserved 6 (Current Alarms 1)': ((response[7] >> 7) & 1), 

            #fine Current Alarms 2
            'Output short-circuit lock': ((response[8] >> 0) & 1),
            'Reserved 7 (Current Alarms 2)': ((response[8] >> 1) & 1),
            'Secondary charge over current lock': ((response[8] >> 2) & 1),
            'Secondary discharge over current lock': ((response[8] >> 3) & 1),
            'Reserved 8 (Current Alarms 2)': ((response[8] >> 4) & 1),
            'Reserved 9 (Current Alarms 2)': ((response[8] >> 5) & 1),
            'Reserved 10 (Current Alarms 2)': ((response[8] >> 6) & 1),
            'Reserved 11 (Current Alarms 2)': ((response[8] >> 7) & 1),
           
            #fine Capacity and other Alarms
            'Low SOC alarm': ((response[9] >> 0) & 1),
            'Intermittent charge': ((response[9] >> 1) & 1),
            'External switch control': ((response[9] >> 2) & 1),
            'Static stand-by sleep': ((response[9] >> 3) & 1),
            'History data recording': ((response[9] >> 4) & 1),
            'Under SOC protect': ((response[9] >> 5) & 1),
            'Active-limited current': ((response[9] >> 6) & 1),
            'Passive-limited current': ((response[9] >> 7) & 1),

            #fine Equalization Alarms
            'Equilibrium module to open': ((response[10] >> 0) & 1),
            'Static equilibrium indicate': ((response[10] >> 1) & 1),
            'Static equilibrium overtime': ((response[10] >> 2) & 1),
            'Equalization temperature limit': ((response[10] >>3) & 1),
            'Reserved 12 (Equalization Alarms)': ((response[10] >> 4) & 1),
            'Reserved 13 (Equalization Alarms)': ((response[10] >> 5) & 1),
            'Reserved 14 (Equalization Alarms)': ((response[10] >> 6) & 1),
            'Reserved 15 (Equalization Alarms)': ((response[10] >> 7) & 1),

            #fine Indicator Alarms
            'Buzzer indicator': ((response[11] >> 0) & 1),
            'LCD display': ((response[11] >> 1) & 1),
            'Manual forced output': ((response[11] >> 2) & 1),
            'Auto forced output': ((response[11] >> 3) & 1),
            'Empty (Indicator Alarms)': ((response[11] >> 4) & 1),            
            'Aerosol detection function': ((response[11] >> 5) & 1),
            'Aerosol normally disconnected mode': ((response[11] >> 6) & 1),
            'Current detector temperature compensation': ((response[11] >> 7) & 1),

            #fine Hard fault Alarms
            'NTC failure': ((response[12] >> 0) & 1),
            'AFE failure': ((response[12] >> 1) & 1),
            'Charge mosfets failure': ((response[12] >> 2) & 1),
            'Discharge mosfets failure': ((response[12] >> 3) & 1),
            'Cell diff failure': ((response[12] >> 4) & 1),
            'Cell break': ((response[12] >> 5) & 1),
            'Key failure': ((response[12] >> 6) & 1),
            'Aerosol Alarm': ((response[12] >> 7) & 1),

        }
        for key, value in func_switch_param_data.items():
            #print(f"{key}: {value}")
            pass
        return func_switch_param_data

    def parse_basic_param(self, response):           
        """Parse the Basic Parameters response from the BMS."""
        
        # Extracting data based on the provided structure
        response = response[2:]

        basic_param_data = {

            'Ntc Number': int.from_bytes(response[1:3], byteorder='big'),  # Byte 3
            'Cell Serial Battery Number': int.from_bytes(response[3:5], byteorder='big'),  # Byte 4
            'Battery High Voltage Recovery(V)': int.from_bytes(response[5:7], byteorder='big') * 0.01,  # Bytes 5-6, 10mV            
            'Battery High Voltage Alarm(V)': int.from_bytes(response[7:9], byteorder='big') * 0.01,  # Bytes 7-8, 10mV
            'Battery Over Voltage Recovery(V)': int.from_bytes(response[9:11], byteorder='big') * 0.01,  # Bytes 9-10, 10mV
            'Battery Over Voltage Protection(V)': int.from_bytes(response[11:13], byteorder='big') * 0.01,  # Bytes 11-12, 10mV
            'Battery Low Voltage Recovery(V)': int.from_bytes(response[13:15], byteorder='big') * 0.01,  # Bytes 13-14, 10mV
            'Battery Low Voltage Alarm(V)': int.from_bytes(response[15:17], byteorder='big') * 0.01,  # Bytes 15-16, 10mV
            'Battery Under Voltage Recovery(V)': int.from_bytes(response[17:19], byteorder='big') * 0.01,  # Bytes 17-18, 10mV
            'Battery Under Voltage Protection(V)': int.from_bytes(response[19:21], byteorder='big') * 0.01,  # Bytes 19-20, 10mV
            'Cell High Voltage Recovery(V)': int.from_bytes(response[21:23], byteorder='big') * 0.001,  # Bytes 21-22, 1mV
            'Cell High Voltage Alarm(V)': int.from_bytes(response[23:25], byteorder='big') * 0.001,  # Bytes 23-24, 1mV
            'Cell Over Voltage Recovery(V)': int.from_bytes(response[25:27], byteorder='big') * 0.001,  # Bytes 25-26, 1mV
            'Cell Over Voltage Protection(V)': int.from_bytes(response[27:29], byteorder='big') * 0.001,  # Bytes 27-28, 1mV
            'Cell Low Voltage Recovery(V)': int.from_bytes(response[29:31], byteorder='big') * 0.001,  # Bytes 29-30, 1mV
            'Cell Low Voltage Alarm(V)': int.from_bytes(response[31:33], byteorder='big') * 0.001,  # Bytes 31-32, 1mV
            'Cell Under Voltage Recovery(V)': int.from_bytes(response[33:35], byteorder='big') * 0.001,  # Bytes 33-34, 1mV
            'Cell Under Voltage Protection(V)': int.from_bytes(response[35:37], byteorder='big') * 0.001,  # Bytes 35-36, 1mV
            'Cell Under Voltage Fault(V)': int.from_bytes(response[37:39], byteorder='big') * 0.001,  # Bytes 37-38
            #'Cell Diff Protection(V)': int.from_bytes(response[39:41], byteorder='big') * 0.001,  # Bytes 39-40
            #'Secondary Charge Current Protection(V)': int.from_bytes(response[41:43], byteorder='big') *0.001,  # Bytes 41-42
            'Charge High Current Recover(A)': int.from_bytes(response[43:45], byteorder='big'),  # Bytes 43-44
            'Charge High Current Alarm(A)': int.from_bytes(response[45:47], byteorder='big'),  # Bytes 45-46
            'Charge Over Current Protection(A)': int.from_bytes(response[47:49], byteorder='big'),  # Bytes 47-48
            'Charge Over Current Time Delay(s)': int.from_bytes(response[49:51], byteorder='big') * 0.1,  # Bytes 49-50
            'Secondary Charge Current Protection 2 (A)': int.from_bytes(response[51:53], byteorder='big'),  # Bytes 51-52
            'Secondary Charge Current Time Delay (ms)': int.from_bytes(response[53:55], byteorder='big') ,  # Bytes 53-54
            'Discharge Low Current Recover(A)': int.from_bytes(response[55:57], byteorder='big', signed = True),  # Bytes 55-56
            'Discharge Low Current Alarm(A)': int.from_bytes(response[57:59], byteorder='big', signed = True),  # Bytes 57-58
            'Discharge Over Current Protection(A)': int.from_bytes(response[59:61], byteorder='big', signed = True),  # Bytes 59-60
            'Discharge Over Current Time Delay(s)': int.from_bytes(response[61:63], byteorder='big') * 0.1,  # Bytes 61-62
            'Secondary Discharge Current Protection(A)': int.from_bytes(response[63:65], byteorder='big', signed = True),  # Bytes 63-64          
            'Secondary Discharge Current Time Delay(ms)': int.from_bytes(response[65:67], byteorder='big'),  # Bytes 65-66

            #'Output Shortcut Protection(A)': int.from_bytes(response[67:69], byteorder='big',signed =True),  # Bytes 67-68 #Value not in BASIC PARAMETERS List
            #'Output Shortcut Time Delay(us)': int.from_bytes(response[69:71], byteorder='big'),  # Bytes 69-70 #Don't know where value comes from (106)
            
            'Over Current Recover Time Delay(s)': int.from_bytes(response[71:73], byteorder='big') * 0.1,  # Bytes 71-72
            'Over Current Lock Times': int.from_bytes(response[73:75], byteorder='big'),  # Bytes 73-74
            'Charge High Switch Limited Time(s)': int.from_bytes(response[75:77], byteorder='big') * 0.1,  # Bytes 75-76
            #'Pulse CurrentA': int.from_bytes(response[77:79], byteorder='big'),  # Bytes 77-78
            'Pulse Time(s)': int.from_bytes(response[79:81], byteorder='big') * 0.1,  # Bytes 79-80

            # Alarms not in BASIC PARAMETERS List
            # 'Precharge Short Percent': int.from_bytes(response[81:83], byteorder='big') * 0.1,  # Bytes 81-82
            # 'Precharge Stop Percent': int.from_bytes(response[83:85], byteorder='big') * 0.1,  # Bytes 83-84
            # 'Precharge Fault Percent': int.from_bytes(response[85:87], byteorder='big') * 0.1,  # Bytes 85-86
            # 'Precharge Over Time': int.from_bytes(response[87:89], byteorder='big'),  # Bytes 87-88
            # Alarms not in BASIC PARAMETERS List

            #'Short-circuit precharge completion rate' - missing alarm, cannot get 100% value

            'Normal precharge completion rate(%)': int.from_bytes(response[89:91], byteorder='big') * 0.1,  # Bytes 89-90
            'Abnormal precharge completion rate(%)': int.from_bytes(response[91:93], byteorder='big') * 0.1,  # Bytes 91-92
            'Precharge over time(s)': int.from_bytes(response[93:95], byteorder='big')*0.1,  # Bytes 93-94
            'Charge High Temperature Recover(C)': int.from_bytes(response[95:97], byteorder='big') * 0.1- K2C,  # Bytes 95-96
            'Charge High Temperature Alarm(C)': int.from_bytes(response[97:99], byteorder='big') * 0.1- K2C,  # Bytes 97-98
            'Charge Over Temperature Recover(C)': int.from_bytes(response[99:101], byteorder='big') * 0.1- K2C,  # Bytes 99-100
            'Charge Over Temperature Protection(C)': int.from_bytes(response[101:103], byteorder='big') * 0.1 - K2C,  # Bytes 101-102
            'Charge Low Temperature Recover(C)': int.from_bytes(response[103:105], byteorder='big') * 0.1 - K2C,  # Bytes 103-104
            'Charge Low Temperature Alarm(C)': int.from_bytes(response[105:107], byteorder='big') * 0.1 - K2C,  # Bytes 105-106
            'Charge Under Temperature Recover(C)': int.from_bytes(response[107:109], byteorder='big') * 0.1 - K2C,  # Bytes 107-108
            'Charge Under Temperature Protection(C)': int.from_bytes(response[109:111], byteorder='big') * 0.1 - K2C,  # Bytes 109-110
            'Discharge High Temperature Recover(C)': int.from_bytes(response[111:113], byteorder='big') * 0.1 - K2C,  # Bytes 111-112
            'Discharge High Temperature Alarm(C)': int.from_bytes(response[113:115], byteorder='big') * 0.1 - K2C,  # Bytes 113-114
            'Discharge Over Temperature Recover(C)': int.from_bytes(response[115:117], byteorder='big') * 0.1 - K2C,  # Bytes 115-116
            'Discharge Over Temperature Protection(C)': int.from_bytes(response[117:119], byteorder='big') * 0.1 - K2C,  # Bytes 117-118
            'Discharge Low Temperature Recover(C)': int.from_bytes(response[119:121], byteorder='big') * 0.1 - K2C,  # Bytes 119-120
            'Discharge Low Temperature Alarm(C)': int.from_bytes(response[121:123], byteorder='big') * 0.1 - K2C,  # Bytes 121-122
            'Discharge Under Temperature Recover(C)': int.from_bytes(response[123:125], byteorder='big') * 0.1 - K2C,  # Bytes 123-124
            'Discharge Under Temperature Protection(C)': int.from_bytes(response[125:127], byteorder='big') * 0.1 - K2C,  # Bytes 125-126
            'High Environment Temperature Recover(C)': int.from_bytes(response[127:129], byteorder='big') * 0.1 - K2C,  # Bytes 127-128
            'High Environment Temperature Alarm(C)': int.from_bytes(response[129:131], byteorder='big') * 0.1 - K2C,  # Bytes 129-130
            'Over Environment Temperature Recover(C)': int.from_bytes(response[131:133], byteorder='big') * 0.1 - K2C,  # Bytes 131-132
            'Over Environment Temperature Protection(C)': int.from_bytes(response[133:135], byteorder='big') * 0.1 - K2C,  # Bytes 133-134
            'Low Environment Temperature Recover(C)': int.from_bytes(response[135:137], byteorder='big') * 0.1 - K2C,  # Bytes 135-136
            'Low Environment Temperature Alarm(C)': int.from_bytes(response[137:139], byteorder='big') * 0.1 - K2C,  # Bytes 137-138
            'Under Environment Temperature Recover(C)': int.from_bytes(response[139:141], byteorder='big') * 0.1 - K2C,  # Bytes 139-140
            'Under Environment Temperature Protection(C)': int.from_bytes(response[141:143], byteorder='big') * 0.1 - K2C,  # Bytes 141-142
            'High Power Temperature Recover(C)': int.from_bytes(response[143:145], byteorder='big') * 0.1 - K2C,  # Bytes 143-144
            #'High Power Temperature Alarm(C)': int.from_bytes(response[145:147], byteorder='big') * 0.1 - K2C,  # Bytes 145-146
            'Over Power Temperature Recover(C)': int.from_bytes(response[147:149], byteorder='big') * 0.1 - K2C,  # Bytes 147-148
            'Over Power Temperature Protection(C)': int.from_bytes(response[149:151], byteorder='big') * 0.1 - K2C,  # Bytes 149-150
            'Cell Heating Stop(C)': int.from_bytes(response[151:153], byteorder='big') * 0.1 - K2C,  # Bytes 151-152
            'Cell Heating Open(C)': int.from_bytes(response[153:155], byteorder='big') * 0.1 - K2C,  # Bytes 153-154
            'Equalization High Temperature Prohibit(C)': int.from_bytes(response[155:157], byteorder='big') * 0.1 - K2C,  # Bytes 155-156
            'Equalization Low Temperature Prohibit(C)': int.from_bytes(response[157:159], byteorder='big') * 0.1 - K2C,  # Bytes 157-158
            'Static Equilibrium Time': int.from_bytes(response[159:161], byteorder='big'),  # Bytes 159-160 (Hours)
            'Equalization Open Voltage(mV)': int.from_bytes(response[161:163], byteorder='big'),  # Bytes 161-162, mV
            'Equalization Open Voltage Difference(mV)': int.from_bytes(response[163:165], byteorder='big'),  # Bytes 163-164, mV
            'Equalization Stop Voltage Difference(mV)': int.from_bytes(response[165:167], byteorder='big'),  # Bytes 165-166, mV
            'SOC Full Release(%)': int.from_bytes(response[167:169], byteorder='big') * 0.1,  # Bytes 167-168, 0.1%
            'SOC Low Recover(%)': int.from_bytes(response[169:171], byteorder='big') * 0.1,  # Bytes 169-170, 0.1%
            'SOC Low Alarm(%)': int.from_bytes(response[171:173], byteorder='big') * 0.1,  # Bytes 171-172, 0.1%
            'SOC Under Recover(%)': int.from_bytes(response[173:175], byteorder='big') * 0.1,  # Bytes 173-174, 0.1%
            'SOC Under Protection(%)': int.from_bytes(response[175:177], byteorder='big') * 0.1,  # Bytes 175-176, 0.1%
            'Battery Rated Capacity(Ah)': int.from_bytes(response[177:179], byteorder='big') * 0.01,  # Bytes 177-178, 10mAh
            #'Battery Total Capacity(Ah)': int.from_bytes(response[179:181], byteorder='big') * 0.01,  # Bytes 179-180, 10mAh
            #'Residual Capacity(Ah)': int.from_bytes(response[181:183], byteorder='big') * 0.01,  # Bytes 181-182, 10mAh
            'Stand-by to Sleep Time(s)': int.from_bytes(response[183:185], byteorder='big'),  # Bytes 183-184, Hours
            'Focs Output Delay Time(s)': int.from_bytes(response[185:187], byteorder='big') * 0.1,  # Bytes 185-186, 0.1s
            'Focs Output Split(Min)': int.from_bytes(response[187:189], byteorder='big'),  # Bytes 187-188, Minutes
            'Pcs Output Timers(s)': int.from_bytes(response[189:191], byteorder='big'),  # Bytes 189-190, Times          
            'Compensating Position 1(Cell)': int.from_bytes(response[191:193], byteorder='big'),  # Bytes 191-192, Cell
            'Position 1 Resistance (mOhm)': int.from_bytes(response[193:195], byteorder='big') * 0.001,  # Bytes 193-194, mΩ            
            'Compensating Position 2(Cell)': int.from_bytes(response[195:197], byteorder='big'),  # Bytes 195-196, Cell
            'Position 2 Resistance(mOhm)': int.from_bytes(response[197:199], byteorder='big') * 0.001,  # Bytes 197-198, mΩ
            'Cell Diff Alarm(mV)': int.from_bytes(response[199:201], byteorder='big'),  # Bytes 199-200, mV
            'Diff Alarm Recover(mV)': int.from_bytes(response[201:203], byteorder='big'),  # Bytes 201-202, mV
            'PCS Request Charge Limit Voltage(V)': int.from_bytes(response[203:205], byteorder='big') * 0.01,  # Bytes 203-204, 10mV
            'PCS Request Charge Limit Current(A)': int.from_bytes(response[205:207], byteorder='big'),  # Bytes 205-206, A
            #'PCS Request Discharge Limit Current': (int.from_bytes(response[207:209], byteorder='big', signed=True)),  # Bytes 207-208, A
            #'PCS Request Discharge Limit Current': (f"Debug: {response[207:209].hex()} -> " + str(int.from_bytes(response[207:209], byteorder='big', signed=True))),  # Bytes 207-208, A

}
        for key, value in basic_param_data.items():
            #print(f"{key}: {value}")
            pass
        return basic_param_data



    def parse_device_info(self, response):
        data = bytes.hex(response)
        data = data[6:-4]
        data = bytes.fromhex(data).decode('ascii')  # Convert hex to ascii string
        manufacturer = data[0:20].replace('\x00', '')
        device_name = data[20:40].replace('\x00', '')
        fw_version = data[40:42].replace('\x00', '')
        bms_sn = data[42:72].replace('\x00', '')
        pack_SN = data[72:102].replace('\x00', '')
        dec_fw_version = str(fw_version[0]+'.'+fw_version[1])
        # print(dec_fw_version)
        # print(type(dec_fw_version))
        return {
            'Manufacturer': manufacturer,
            'Device Name': device_name,
            'Firmware Version': dec_fw_version,
            'BMS Serial Number': bms_sn,
            'Pack Serial Number': pack_SN
        }
    

    
    def close(self):
        """Close the serial connection"""
        self.serial.close()

def main():
    # Create BMS communicator instance
    bms = BMSCommunicator(port='/dev/ttyUSB0', baudrate=19200)  
    
    # Get pack information
    pack_info = bms.get_pack_info()
    
        
    bms.close()

if __name__ == "__main__":
    main()

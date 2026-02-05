import json
import os
import time
import datetime
import random
import threading
import RPi.GPIO as GPIO  # Add GPIO library
from main import BMSCommunicator
from tv_tools import outputJSON_local
from tv_tools import root
from tv_tools import test,store_pack_info

class BMSTestApp:
    # GPIO pins
    BLUE_LED_PIN = 17
    YELLOW_LED_PIN = 27
    GREEN_LED_PIN = 22
    RED_LED_PIN = 23
    START_BTN_PIN = 5
    RESET_BTN_PIN = 6

    def __init__(self):

        # Load local Production config file        
        NB_file = 'config.json'
        with open(NB_file, 'r') as f:
            self.config = json.load(f)        
        #Load local config folder
             

        # #Open local RMA config file         
        # t_file = 'configRMA.json'
        # with open(t_file, 'r') as f:
        #     self.configRMA = json.load(f)
            #print(self.configRMA)
        # #Open local RMA config file     

        
        #Load local config folder

        #Liam Start
        self.ts = None
        self.current_operator = None
        self.test_desc = "System ATP - Battery Validation Test"  # Example attribute
        self.test_jig = "BMS Test Station Test Jig"
        self.device_id = "Device ID" #SZ-G8K2-999999
        self.serialnr = "Serial Number" #"SZS:SZ-G8K2-999999 / SC:405-1001160 / JN:MF999999"
        self.jobnr = "JN:MF999999" #JN:MF999999
        self.prefix = "NA"
        self.procedure = "BMS ATP Test"
        self.productGroup = "Batteries"
        self.supplierserial = "Supplier Serial" #"SP59B2308230186" - currrently sz Serial Number
        self.lowerlevelID = "NA"
        self.tests = []
        self.errors = []
        self.result = "Undetermined"  # Can be dynamic based on the test result

        # GPIO setup
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.BLUE_LED_PIN, GPIO.OUT)
        GPIO.setup(self.YELLOW_LED_PIN, GPIO.OUT)
        GPIO.setup(self.GREEN_LED_PIN, GPIO.OUT)
        GPIO.setup(self.RED_LED_PIN, GPIO.OUT)
        GPIO.setup(self.START_BTN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.RESET_BTN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        # Initial LED state: blue ON, others OFF
        GPIO.output(self.BLUE_LED_PIN, GPIO.HIGH)
        GPIO.output(self.YELLOW_LED_PIN, GPIO.LOW)
        GPIO.output(self.GREEN_LED_PIN, GPIO.LOW)
        GPIO.output(self.RED_LED_PIN, GPIO.LOW)

        # Start button monitoring in a thread
        self.test_running = False
        self.monitor_thread = threading.Thread(target=self.monitor_buttons, daemon=True)
        self.monitor_thread.start()

    filepath = os.path.join("data", 'pack_info.json') #works

    @staticmethod      
    def load_pack_info(filepath):
        """Load the pack information from the JSON file."""
        try:
            # Open the JSON file in read mode
            with open(filepath, 'r') as json_file:
                # Load and parse the JSON data into a Python dictionary
                pack_info = json.load(json_file)
                #print(pack_info)
                return pack_info
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            return None

       
    
    data = load_pack_info(filepath)
    device_info = data.get('Acquire Device Manufacture Info', {})
    supplier_info = device_info.get('Manufacturer', 'Unknown Device')
    device_name = device_info.get('Device  Name', 'Unknown Device') #get device name
    sup_serial_number = device_info.get('BMS Serial Number','Unknown Device') #get supplier serial number
    
    # #output Pack_info to FTP server in complete_pack_data folder

    def store_test_data(self):
        """Store relevant test data into a JSON file."""
        ts = int(time.time())
        tester = "Field Technician"
        test_desc = "Mobile BMS ATP Test"
        test_jig = "Mobile BMS Test Jig"
        device_id = "Still Make"
        prefix = "NA"
        jobnr = "NA"
        serialnr = "NA"
        procedure = "BMS ATP Test"
        productGroup = "Batteries"
        lowerlevelID = "NA"

        # Create TestFile1 object
        TestFile1 = root(
            ts, tester, test_desc, test_jig, device_id, 
            prefix, jobnr, serialnr, procedure, 
            productGroup, self.sup_serial_number, lowerlevelID, 
            self.tests, self.errors, self.result
        )

        # Create directory structure if it doesn't exist
        result_dir = os.path.join(os.getcwd(), "Test_Result_Dump_New", "Production")
        os.makedirs(result_dir, exist_ok=True)

        # Output TestFile locally with timestamp to ensure unique filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        result_filename = f"{self.sup_serial_number}_{timestamp}_{ts}_results.json"
        result_filepath = os.path.join(result_dir, result_filename)

        try:
            outputJSON_local(TestFile1, result_filepath)
            print(f"Test results saved to {result_filepath}")
        except Exception as e:
            print(f"Error saving test results: {e}")

    def load_test_criteria(self):
        with open('config.json', 'r') as criteria_file:
            return json.load(criteria_file)


    # Validate the test results against the criteria
    def validate_results(self, pack_info):
        criteria = self.load_test_criteria()
        criteria['Acquire Device Manufacture Info']['BMS Serial Number'] = pack_info['Acquire Device Manufacture Info']['BMS Serial Number']
        
        errors = []  # List to hold error messages

        # Validate PIA
        for key, value in criteria['PIA'].items():
            if key in ['Raw Response', 'BMS Serial Number']:
                continue  # Skip these fields
            if isinstance(value, list):  # Range check
                if not (value[0] <= pack_info['PIA'][key] <= value[1]):
                    errors.append(f"\nPIA - {key} out of range: {pack_info['PIA'][key]} not in {value}")
            else:  # Exact match
                if pack_info['PIA'][key] != value:
                    errors.append(f"\nPIA - {key} mismatch:\nExpected -> {value}\nReceived -> {pack_info['PIA'][key]}")

        # Validate PIC
        for key, value in criteria['PIC'].items():
            if key == 'Raw Response':  # Skip this field in PIC
                continue
            if pack_info['PIC'][key] != value:
                errors.append(f"\nPIC - {key} mismatch:\nExpected -> {value}\nReceived -> {pack_info['PIC'][key]}")

        # Validate Function Switch Parameters
        for key, expected_value in criteria['Function Switch Param'].items():
            if key not in pack_info.get('Function Switch Param', {}):
                errors.append(f"\nFunction Switch Parameter - {key} missing in pack_info.")
                continue

            actual_value = pack_info['Function Switch Param'][key]
            if isinstance(expected_value, list):
                if actual_value not in expected_value:
                    errors.append(
                        f"\nFunction Switch - {key} mismatch:\n"
                        f"Expected one of -> {expected_value}\n"
                        f"Received -> {actual_value}"
                    )
            elif actual_value != expected_value:
                errors.append(
                    f"\nFunction Switch - {key} mismatch:\n"
                    f"Expected -> {expected_value}\n"
                    f"Received -> {actual_value}"
                )

        # Validate Basic Parameters

        for key, value in criteria['Basic Param'].items():
            if key in 'Raw Response':
                continue  # Skip these fields
            if isinstance(value, list):  # Range check
                if not (value[0] <= pack_info['Basic Param'][key] <= value[1]):
                    errors.append(f"\nBasic Param - {key} out of range: {pack_info['Basic Param'][key]} not in {value}")
            else:  # Exact match
                if pack_info['Basic Param'][key] != value:
                    errors.append(f"\nBasic Param - {key} mismatch:\nExpected -> {value}\nReceived -> {pack_info['Basic Param'][key]}")


        for key, value in criteria['Acquire Device Manufacture Info'].items():
            if key == ['Manufacturer', 'Device Name','BMS Serial Number','Pack Serial Number']:  # Skip this field in PIC
                continue
            if pack_info['Acquire Device Manufacture Info'][key] != value:
                #errors.append(f"Acquire Device Manufacture Info {key} mismatch:\nExpected firmware version -> {value[0]}.{value[1]}\nReceived firmware version -> {pack_info['Acquire Device Manufacture Info'][key][0]}.{pack_info['Acquire Device Manufacture Info'][key][1]}")
                errors.append(f"\nExpected firmware version -> {value}\nReceived firmware version -> {pack_info['Acquire Device Manufacture Info'][key]}")

        return errors


    def start_test(self):
        try:
            bms = BMSCommunicator(port='/dev/ttyUSB0', baudrate=19200)
            pack_info = bms.get_pack_info()

            #Store complete pack info

            pack_filename = f"{self.sup_serial_number}_complete_pack_info.json"
            print(f'Pack file name: {pack_filename}')

            # pack_filepath = os.getcwd() + "/Complete_Pack_Info_dump/Production/" + pack_filename
            # pack_ftp_folder = 'BMS_Test_Station_New/complete_pack_data/Production'

            json_path = os.path.join("Complete_Pack_Info_dump/Production/", pack_filename)
            with open(json_path, 'w') as f:
                json.dump(pack_info, f, indent=4)

            #Store complete pack info

            bms.close()

            if pack_info:
                errors = self.validate_results(pack_info)
                self.errors = errors

                self.tests = []
                filepath2 = os.path.join("data", 'pack_info.json') #works
                ### config for RMA

                #New Battery Packs
                ###############################################################################################
                config_pia =self.config["PIA"]
                config_device = self.config["Acquire Device Manufacture Info"]
                config_alarms = self.config["Alarms"]
                config_func_switch = self.config["Function Switch Param"]
                config_basic_params = self.config["Basic Param"]

                pack_data = BMSTestApp.load_pack_info(filepath2)
                Device_info = pack_data.get('Acquire Device Manufacture Info')
                PIA_info = pack_data.get('PIA')
                Alarms_info = pack_data.get('Alarms')
                Function_Switch_info = pack_data.get('Function Switch Param')
                Basic_Param_info = pack_data.get('Basic Param')
            
                #Test Data for Firmware Version
                if float(config_device["Firmware Version"]) == float(Device_info["Firmware Version"]):
                    device_result = "PASS"
                else:
                    device_result = "FAIL"
                
                firm_test = test(list(config_device.keys())[2],
                                    ((config_device["Firmware Version"])),
                                    (Device_info["Firmware Version"]), device_result, "Firmware Version Check", "NA","NA")
                

                #Test Data for Pack Voltage
                if config_pia["Pack Voltage"][0] <= PIA_info["Pack Voltage"] <= config_pia["Pack Voltage"][1]:
                    pack_result = "PASS"
                else:
                    pack_result = "FAIL"

                pack_test = test(next(iter(config_pia)),
                                    (config_pia["Pack Voltage"][0]+config_pia["Pack Voltage"][1])/2,
                                    PIA_info["Pack Voltage"], pack_result, "Pack Voltage Test", str(config_pia["Pack Voltage"]),"NA")
                
                                            
                #Test Data for Current
                
                #if config_pia["Current"] >= PIA_info["Current"]:
                #    current_result = "PASS"
                #else:
                #    current_result = "FAIL"
                #
                #current_test = test(list(config_pia.keys())[1],
                #                (config_pia["Current"]),
                #                   PIA_info["Current"], current_result, "Current Test", "NA","NA")
                
                #Test Data for Total Capacity        

                                                
                
                #Test Data for SOC               
                if config_pia["SOC"][0] <= PIA_info["SOC"] <= config_pia["SOC"][1]:
                    soc_result = "PASS"
                else:
                    soc_result = "FAIL"

                soc_test = test(list(config_pia.keys())[1],
                                    (config_pia["SOC"][0]+config_pia["SOC"][1])/2,
                                    PIA_info["SOC"], soc_result, "SOC", str(config_pia["SOC"]),"NA")
                
                #Test Data for SOH 
                                
                #if config_pia["SOH"][0] <= PIA_info["SOH"] <= config_pia["SOH"][1]:
                #    soh_result = "PASS"
                #else:
                #    soc_result = "FAIL"
                #
                #soh_test = test(list(config_pia.keys())[6],
                #                    (config_pia["SOH"][0]+config_pia["SOH"][1])/2,
                #                    PIA_info["SOH"], soh_result, "SOH", str(config_pia["SOH"]),"NA")           
                

                if (
                    config_func_switch["Cell high voltage alarm"] == Function_Switch_info["Cell high voltage alarm"] and
                    config_func_switch["Cell over voltage protection"] == Function_Switch_info["Cell over voltage protection"] and
                    config_func_switch["Cell low voltage alarm"] == Function_Switch_info["Cell low voltage alarm"] and
                    config_func_switch["Cell under voltage protection"] == Function_Switch_info["Cell under voltage protection"] and
                    config_func_switch["Battery high voltage alarm"] == Function_Switch_info["Battery high voltage alarm"] and
                    config_func_switch["Battery over voltage protection"] == Function_Switch_info["Battery over voltage protection"] and
                    config_func_switch["Battery low voltage alarm"] == Function_Switch_info["Battery low voltage alarm"] and
                    config_func_switch["Battery under voltage protection"] == Function_Switch_info["Battery under voltage protection"] and
                    config_func_switch["Charge high temperature alarm"] == Function_Switch_info["Charge high temperature alarm"] and
                    config_func_switch["Charge over temperature protection"] == Function_Switch_info["Charge over temperature protection"] and
                    config_func_switch["Charge low temperature alarm"] == Function_Switch_info["Charge low temperature alarm"] and
                    config_func_switch["Charge under temperature protection"] == Function_Switch_info["Charge under temperature protection"] and
                    config_func_switch["Discharge high temperature alarm"] == Function_Switch_info["Discharge high temperature alarm"] and
                    config_func_switch["Discharge over temperature protection"] == Function_Switch_info["Discharge over temperature protection"] and
                    config_func_switch["Discharge low temperature alarm"] == Function_Switch_info["Discharge low temperature alarm"] and
                    config_func_switch["Discharge under temperature protection"] == Function_Switch_info["Discharge under temperature protection"] and
                    config_func_switch["High ambient temperature alarm"] == Function_Switch_info["High ambient temperature alarm"] and
                    config_func_switch["Over ambient temperature protection"] == Function_Switch_info["Over ambient temperature protection"] and
                    config_func_switch["Low ambient temperature alarm"] == Function_Switch_info["Low ambient temperature alarm"] and
                    config_func_switch["Under ambient temperature protection"] == Function_Switch_info["Under ambient temperature protection"] and
                    config_func_switch["Power high temperature alarm"] == Function_Switch_info["Power high temperature alarm"] and
                    config_func_switch["Power over temperature protection"] == Function_Switch_info["Power over temperature protection"] and
                    config_func_switch["Cell temperature low heating"] == Function_Switch_info["Cell temperature low heating"] and
                    config_func_switch["Cell voltage Fault (Reserved)"] == Function_Switch_info["Cell voltage Fault (Reserved)"] and
                    (config_func_switch["Focs Output"][0] == Function_Switch_info["Focs Output"] or config_func_switch["Focs Output"][1] == Function_Switch_info["Focs Output"]) and
                    config_func_switch["Heat dissipation turned on"] == Function_Switch_info["Heat dissipation turned on"] and
                    config_func_switch["CapLeds idle display"] == Function_Switch_info["CapLeds idle display"] and
                    config_func_switch["Reserved 1 (Voltage Alarms 2)"] == Function_Switch_info["Reserved 1 (Voltage Alarms 2)"] and
                    config_func_switch["Reserved 2 (Voltage Alarms 2)"] == Function_Switch_info["Reserved 2 (Voltage Alarms 2)"] and
                    config_func_switch["Reserved 3 (Voltage Alarms 2)"] == Function_Switch_info["Reserved 3 (Voltage Alarms 2)"] and
                    config_func_switch["Reserved 4 (Voltage Alarms 2)"] == Function_Switch_info["Reserved 4 (Voltage Alarms 2)"] and
                    config_func_switch["Reserved 5 (Voltage Alarms 2)"] == Function_Switch_info["Reserved 5 (Voltage Alarms 2)"] and
                    config_func_switch["Charge current alarm"] == Function_Switch_info["Charge current alarm"] and
                    config_func_switch["Charge over current protection"] == Function_Switch_info["Charge over current protection"] and
                    config_func_switch["Secondary charge over current protection"] == Function_Switch_info["Secondary charge over current protection"] and
                    config_func_switch["Discharge current alarm"] == Function_Switch_info["Discharge current alarm"] and
                    config_func_switch["Discharge over current protection"] == Function_Switch_info["Discharge over current protection"] and
                    config_func_switch["Secondary discharge over current protection"] == Function_Switch_info["Secondary discharge over current protection"] and
                    config_func_switch["Output short-circuit protection"] == Function_Switch_info["Output short-circuit protection"] and
                    config_func_switch["Reserved 6 (Current Alarms 1)"] == Function_Switch_info["Reserved 6 (Current Alarms 1)"] and
                    config_func_switch["Output short-circuit lock"] == Function_Switch_info["Output short-circuit lock"] and
                    (config_func_switch["Reserved 7 (Current Alarms 2)"][0] == Function_Switch_info["Reserved 7 (Current Alarms 2)"] or config_func_switch["Reserved 7 (Current Alarms 2)"][1] == Function_Switch_info["Reserved 7 (Current Alarms 2)"]) and
                    config_func_switch["Secondary charge over current lock"] == Function_Switch_info["Secondary charge over current lock"] and
                    config_func_switch["Secondary discharge over current lock"] == Function_Switch_info["Secondary discharge over current lock"] and
                    config_func_switch["Reserved 8 (Current Alarms 2)"] == Function_Switch_info["Reserved 8 (Current Alarms 2)"] and
                    config_func_switch["Reserved 9 (Current Alarms 2)"] == Function_Switch_info["Reserved 9 (Current Alarms 2)"] and
                    config_func_switch["Reserved 10 (Current Alarms 2)"] == Function_Switch_info["Reserved 10 (Current Alarms 2)"] and
                    config_func_switch["Reserved 11 (Current Alarms 2)"] == Function_Switch_info["Reserved 11 (Current Alarms 2)"] and
                    config_func_switch["Low SOC alarm"] == Function_Switch_info["Low SOC alarm"] and
                    config_func_switch["Intermittent charge"] == Function_Switch_info["Intermittent charge"] and
                    config_func_switch["External switch control"] == Function_Switch_info["External switch control"] and
                    config_func_switch["Static stand-by sleep"] == Function_Switch_info["Static stand-by sleep"] and
                    config_func_switch["History data recording"] == Function_Switch_info["History data recording"] and
                    config_func_switch["Under SOC protect"] == Function_Switch_info["Under SOC protect"] and
                    config_func_switch["Active-limited current"] == Function_Switch_info["Active-limited current"] and
                    config_func_switch["Passive-limited current"] == Function_Switch_info["Passive-limited current"] and
                    config_func_switch["Equilibrium module to open"] == Function_Switch_info["Equilibrium module to open"] and
                    config_func_switch["Static equilibrium indicate"] == Function_Switch_info["Static equilibrium indicate"] and
                    config_func_switch["Static equilibrium overtime"] == Function_Switch_info["Static equilibrium overtime"] and
                    config_func_switch["Equalization temperature limit"] == Function_Switch_info["Equalization temperature limit"] and
                    config_func_switch["Reserved 12 (Equalization Alarms)"] == Function_Switch_info["Reserved 12 (Equalization Alarms)"] and
                    config_func_switch["Reserved 13 (Equalization Alarms)"] == Function_Switch_info["Reserved 13 (Equalization Alarms)"] and
                    config_func_switch["Reserved 14 (Equalization Alarms)"] == Function_Switch_info["Reserved 14 (Equalization Alarms)"] and
                    config_func_switch["Reserved 15 (Equalization Alarms)"] == Function_Switch_info["Reserved 15 (Equalization Alarms)"] and
                    (config_func_switch["Buzzer indicator"][0] == Function_Switch_info["Buzzer indicator"] or config_func_switch["Buzzer indicator"][1] == Function_Switch_info["Buzzer indicator"]) and
                    config_func_switch["LCD display"] == Function_Switch_info["LCD display"] and
                    config_func_switch["Manual forced output"] == Function_Switch_info["Manual forced output"] and
                    config_func_switch["Auto forced output"] == Function_Switch_info["Auto forced output"] and
                    config_func_switch["Empty (Indicator Alarms)"] == Function_Switch_info["Empty (Indicator Alarms)"] and
                    config_func_switch["Aerosol detection function"] == Function_Switch_info["Aerosol detection function"] and
                    config_func_switch["Aerosol normally disconnected mode"] == Function_Switch_info["Aerosol normally disconnected mode"] and
                    config_func_switch["Current detector temperature compensation"] == Function_Switch_info["Current detector temperature compensation"] and
                    config_func_switch["NTC failure"] == Function_Switch_info["NTC failure"] and
                    config_func_switch["AFE failure"] == Function_Switch_info["AFE failure"] and
                    config_func_switch["Charge mosfets failure"] == Function_Switch_info["Charge mosfets failure"] and
                    config_func_switch["Discharge mosfets failure"] == Function_Switch_info["Discharge mosfets failure"] and
                    config_func_switch["Cell diff failure"] == Function_Switch_info["Cell diff failure"] and
                    config_func_switch["Cell break"] == Function_Switch_info["Cell break"] and
                    config_func_switch["Key failure"] == Function_Switch_info["Key failure"] and
                    config_func_switch["Aerosol Alarm"] == Function_Switch_info["Aerosol Alarm"]
                ):
                    func_switch_result = "PASS"
                else:
                    func_switch_result = "FAIL"

                func_switch_test = test("Function Switch", "NA", "NA", (func_switch_result), "Function Switch Param Check", "NA", "NA")

                # Check Function Switch Parameters

                # Check Basic Param

                if(
                    config_basic_params["Ntc Number"] == Basic_Param_info["Ntc Number"] and
                    config_basic_params["Cell Serial Battery Number"] == Basic_Param_info["Cell Serial Battery Number"] and
                    config_basic_params["Battery High Voltage Recovery(V)"] == Basic_Param_info["Battery High Voltage Recovery(V)"] and
                    config_basic_params["Battery High Voltage Alarm(V)"] == Basic_Param_info["Battery High Voltage Alarm(V)"] and
                    config_basic_params["Battery Over Voltage Recovery(V)"] == Basic_Param_info["Battery Over Voltage Recovery(V)"] and
                    config_basic_params["Battery Over Voltage Protection(V)"] == Basic_Param_info["Battery Over Voltage Protection(V)"] and
                    config_basic_params["Battery Low Voltage Recovery(V)"] == Basic_Param_info["Battery Low Voltage Recovery(V)"] and
                    config_basic_params["Battery Low Voltage Alarm(V)"] == Basic_Param_info["Battery Low Voltage Alarm(V)"] and
                    config_basic_params["Battery Under Voltage Recovery(V)"] == Basic_Param_info["Battery Under Voltage Recovery(V)"] and
                    config_basic_params["Battery Under Voltage Protection(V)"] == Basic_Param_info["Battery Under Voltage Protection(V)"] and
                    config_basic_params["Cell High Voltage Recovery(V)"] == Basic_Param_info["Cell High Voltage Recovery(V)"] and
                    config_basic_params["Cell High Voltage Alarm(V)"] == Basic_Param_info["Cell High Voltage Alarm(V)"] and
                    config_basic_params["Cell Over Voltage Recovery(V)"] == Basic_Param_info["Cell Over Voltage Recovery(V)"] and
                    config_basic_params["Cell Over Voltage Protection(V)"] == Basic_Param_info["Cell Over Voltage Protection(V)"] and
                    config_basic_params["Cell Low Voltage Recovery(V)"] == Basic_Param_info["Cell Low Voltage Recovery(V)"] and
                    config_basic_params["Cell Low Voltage Alarm(V)"] == Basic_Param_info["Cell Low Voltage Alarm(V)"] and
                    config_basic_params["Cell Under Voltage Recovery(V)"] == Basic_Param_info["Cell Under Voltage Recovery(V)"] and
                    config_basic_params["Cell Under Voltage Protection(V)"] == Basic_Param_info["Cell Under Voltage Protection(V)"] and
                    config_basic_params["Cell Under Voltage Fault(V)"] == Basic_Param_info["Cell Under Voltage Fault(V)"] and
                    #config_basic_params["Cell Diff Protection(V)"] == Basic_Param_info["Cell Diff Protection(V)"] and
                    #config_basic_params["Secondary Charge Current Protection(V)"] == Basic_Param_info["Secondary Charge Current Protection(V)"] and
                    config_basic_params["Charge High Current Recover(A)"] == Basic_Param_info["Charge High Current Recover(A)"] and
                    config_basic_params["Charge High Current Alarm(A)"] == Basic_Param_info["Charge High Current Alarm(A)"] and
                    config_basic_params["Charge Over Current Protection(A)"] == Basic_Param_info["Charge Over Current Protection(A)"] and
                    config_basic_params["Charge Over Current Time Delay(s)"] == Basic_Param_info["Charge Over Current Time Delay(s)"] and
                    config_basic_params["Secondary Charge Current Protection 2 (A)"] == Basic_Param_info["Secondary Charge Current Protection 2 (A)"] and
                    config_basic_params["Secondary Charge Current Time Delay (ms)"] == Basic_Param_info["Secondary Charge Current Time Delay (ms)"] and
                    config_basic_params["Discharge Low Current Recover(A)"] == Basic_Param_info["Discharge Low Current Recover(A)"] and
                    config_basic_params["Discharge Low Current Alarm(A)"] == Basic_Param_info["Discharge Low Current Alarm(A)"] and
                    config_basic_params["Discharge Over Current Protection(A)"] == Basic_Param_info["Discharge Over Current Protection(A)"] and
                    config_basic_params["Discharge Over Current Time Delay(s)"] == Basic_Param_info["Discharge Over Current Time Delay(s)"] and
                    config_basic_params["Secondary Discharge Current Protection(A)"] == Basic_Param_info["Secondary Discharge Current Protection(A)"] and
                    config_basic_params["Secondary Discharge Current Time Delay(ms)"] == Basic_Param_info["Secondary Discharge Current Time Delay(ms)"] and
                    config_basic_params["Over Current Recover Time Delay(s)"] == Basic_Param_info["Over Current Recover Time Delay(s)"] and
                    config_basic_params["Over Current Lock Times"] == Basic_Param_info["Over Current Lock Times"] and
                    config_basic_params["Charge High Switch Limited Time(s)"] == Basic_Param_info["Charge High Switch Limited Time(s)"] and
                    #config_basic_params["Pulse CurrentA"] == Basic_Param_info["Pulse CurrentA"] and
                    config_basic_params["Pulse Time(s)"] == Basic_Param_info["Pulse Time(s)"] and
                    config_basic_params["Normal precharge completion rate(%)"] == Basic_Param_info["Normal precharge completion rate(%)"] and
                    config_basic_params["Abnormal precharge completion rate(%)"] == Basic_Param_info["Abnormal precharge completion rate(%)"] and
                    config_basic_params["Precharge over time(s)"] == Basic_Param_info["Precharge over time(s)"] and
                    config_basic_params["Charge High Temperature Recover(C)"] == Basic_Param_info["Charge High Temperature Recover(C)"] and
                    config_basic_params["Charge High Temperature Alarm(C)"] == Basic_Param_info["Charge High Temperature Alarm(C)"] and
                    config_basic_params["Charge Over Temperature Recover(C)"] == Basic_Param_info["Charge Over Temperature Recover(C)"] and
                    config_basic_params["Charge Over Temperature Protection(C)"] == Basic_Param_info["Charge Over Temperature Protection(C)"] and
                    config_basic_params["Charge Low Temperature Recover(C)"] == Basic_Param_info["Charge Low Temperature Recover(C)"] and
                    config_basic_params["Charge Low Temperature Alarm(C)"] == Basic_Param_info["Charge Low Temperature Alarm(C)"] and
                    config_basic_params["Charge Under Temperature Recover(C)"] == Basic_Param_info["Charge Under Temperature Recover(C)"] and
                    config_basic_params["Charge Under Temperature Protection(C)"] == Basic_Param_info["Charge Under Temperature Protection(C)"] and
                    config_basic_params["Discharge High Temperature Recover(C)"] == Basic_Param_info["Discharge High Temperature Recover(C)"] and
                    config_basic_params["Discharge High Temperature Alarm(C)"] == Basic_Param_info["Discharge High Temperature Alarm(C)"] and
                    config_basic_params["Discharge Over Temperature Recover(C)"] == Basic_Param_info["Discharge Over Temperature Recover(C)"] and
                    config_basic_params["Discharge Over Temperature Protection(C)"] == Basic_Param_info["Discharge Over Temperature Protection(C)"] and
                    config_basic_params["Discharge Low Temperature Recover(C)"] == Basic_Param_info["Discharge Low Temperature Recover(C)"] and
                    config_basic_params["Discharge Low Temperature Alarm(C)"] == Basic_Param_info["Discharge Low Temperature Alarm(C)"] and
                    config_basic_params["Discharge Under Temperature Recover(C)"] == Basic_Param_info["Discharge Under Temperature Recover(C)"] and
                    config_basic_params["Discharge Under Temperature Protection(C)"] == Basic_Param_info["Discharge Under Temperature Protection(C)"] and
                    config_basic_params["High Environment Temperature Recover(C)"] == Basic_Param_info["High Environment Temperature Recover(C)"] and
                    config_basic_params["High Environment Temperature Alarm(C)"] == Basic_Param_info["High Environment Temperature Alarm(C)"] and
                    config_basic_params["Over Environment Temperature Recover(C)"] == Basic_Param_info["Over Environment Temperature Recover(C)"] and
                    config_basic_params["Over Environment Temperature Protection(C)"] == Basic_Param_info["Over Environment Temperature Protection(C)"] and
                    config_basic_params["Low Environment Temperature Recover(C)"] == Basic_Param_info["Low Environment Temperature Recover(C)"] and
                    config_basic_params["Low Environment Temperature Alarm(C)"] == Basic_Param_info["Low Environment Temperature Alarm(C)"] and
                    config_basic_params["Under Environment Temperature Recover(C)"] == Basic_Param_info["Under Environment Temperature Recover(C)"] and
                    config_basic_params["Under Environment Temperature Protection(C)"] == Basic_Param_info["Under Environment Temperature Protection(C)"] and
                    config_basic_params["High Power Temperature Recover(C)"] == Basic_Param_info["High Power Temperature Recover(C)"] and
                    #config_basic_params["High Power Temperature Alarm(C)"] == Basic_Param_info["High Power Temperature Alarm(C)"] and
                    config_basic_params["Over Power Temperature Recover(C)"] == Basic_Param_info["Over Power Temperature Recover(C)"] and
                    config_basic_params["Over Power Temperature Protection(C)"] == Basic_Param_info["Over Power Temperature Protection(C)"] and
                    config_basic_params["Cell Heating Stop(C)"] == Basic_Param_info["Cell Heating Stop(C)"] and
                    config_basic_params["Cell Heating Open(C)"] == Basic_Param_info["Cell Heating Open(C)"] and
                    config_basic_params["Equalization High Temperature Prohibit(C)"] == Basic_Param_info["Equalization High Temperature Prohibit(C)"] and
                    config_basic_params["Equalization Low Temperature Prohibit(C)"] == Basic_Param_info["Equalization Low Temperature Prohibit(C)"] and
                    config_basic_params["Static Equilibrium Time"] == Basic_Param_info["Static Equilibrium Time"] and
                    config_basic_params["Equalization Open Voltage(mV)"] == Basic_Param_info["Equalization Open Voltage(mV)"] and
                    config_basic_params["Equalization Open Voltage Difference(mV)"] == Basic_Param_info["Equalization Open Voltage Difference(mV)"] and
                    config_basic_params["Equalization Stop Voltage Difference(mV)"] == Basic_Param_info["Equalization Stop Voltage Difference(mV)"] and
                    config_basic_params["SOC Full Release(%)"] == Basic_Param_info["SOC Full Release(%)"] and
                    config_basic_params["SOC Low Recover(%)"] == Basic_Param_info["SOC Low Recover(%)"] and
                    config_basic_params["SOC Low Alarm(%)"] == Basic_Param_info["SOC Low Alarm(%)"] and
                    config_basic_params["SOC Under Recover(%)"] == Basic_Param_info["SOC Under Recover(%)"] and
                    config_basic_params["SOC Under Protection(%)"] == Basic_Param_info["SOC Under Protection(%)"] and
                    config_basic_params["Battery Rated Capacity(Ah)"] == Basic_Param_info["Battery Rated Capacity(Ah)"] and                  
                    #(config_basic_params["Battery Total Capacity(Ah)"][0] <= Basic_Param_info["Battery Total Capacity(Ah)"] <= config_basic_params["Battery Total Capacity(Ah)"][1]) and
                    #(config_basic_params["Residual Capacity(Ah)"][0] <= Basic_Param_info["Residual Capacity(Ah)"] <= config_basic_params["Battery Total Capacity(Ah)"][1]) and
                    config_basic_params["Stand-by to Sleep Time(s)"] == Basic_Param_info["Stand-by to Sleep Time(s)"] and
                    config_basic_params["Focs Output Delay Time(s)"] == Basic_Param_info["Focs Output Delay Time(s)"] and
                    config_basic_params["Focs Output Split(Min)"] == Basic_Param_info["Focs Output Split(Min)"] and
                    config_basic_params["Pcs Output Timers(s)"] == Basic_Param_info["Pcs Output Timers(s)"] and
                    config_basic_params["Compensating Position 1(Cell)"] == Basic_Param_info["Compensating Position 1(Cell)"] and
                    config_basic_params["Position 1 Resistance (mOhm)"] == Basic_Param_info["Position 1 Resistance (mOhm)"] and
                    config_basic_params["Compensating Position 2(Cell)"] == Basic_Param_info["Compensating Position 2(Cell)"] and
                    config_basic_params["Position 2 Resistance(mOhm)"] == Basic_Param_info["Position 2 Resistance(mOhm)"] and
                    config_basic_params["Cell Diff Alarm(mV)"] == Basic_Param_info["Cell Diff Alarm(mV)"] and
                    config_basic_params["Diff Alarm Recover(mV)"] == Basic_Param_info["Diff Alarm Recover(mV)"] and
                    config_basic_params["PCS Request Charge Limit Voltage(V)"] == Basic_Param_info["PCS Request Charge Limit Voltage(V)"] and
                    config_basic_params["PCS Request Charge Limit Current(A)"] == Basic_Param_info["PCS Request Charge Limit Current(A)"]


                ):
                    basic_params_result = "PASS"
                else:
                    basic_params_result = "FAIL"

                basic_params_test = test("Basic Parameters", "NA", "NA", (basic_params_result), "Basic Parameters Check", "NA", "NA")


                #Append test dictionaries to test object
                self.tests.append(firm_test.__dict__)
                #self.tests.append(current_test.__dict__)
                self.tests.append(pack_test.__dict__)
                self.tests.append(soc_test.__dict__)
                #self.tests.append(soh_test.__dict__)
                self.tests.append(func_switch_test.__dict__)
                self.tests.append(basic_params_test.__dict__)

                if not self.errors:
                    self.result = "Pass"
                    print("Test Passed")
                    #self.control_led("yellow")
                    #time.sleep(2)
                    self.control_led("green")
                    self.store_test_data()
                else:
                    self.result = "Fail"
                    print("Test Failed")
                    #self.control_led("yellow")
                    #time.sleep(2)
                    self.control_led("red")
                    self.store_test_data()
            # After test, yellow LED off
            GPIO.output(self.YELLOW_LED_PIN, GPIO.LOW)
        except Exception as e:
            print(f"Error during test: {e}")
            self.control_led("red")
            GPIO.output(self.YELLOW_LED_PIN, GPIO.LOW)
        finally:
            self.test_running = True  # Remain in test state until reset

    def monitor_buttons(self):
        while True:
            # Start button pressed (active low)
            if GPIO.input(self.START_BTN_PIN) == GPIO.LOW and not self.test_running:
                self.test_running = True
                self.handle_start_button()
                # Debounce
                while GPIO.input(self.START_BTN_PIN) == GPIO.LOW:
                    time.sleep(0.05)
            # Reset button pressed (active low)
            if GPIO.input(self.RESET_BTN_PIN) == GPIO.LOW and self.test_running:
                self.handle_reset_button()
                # Debounce
                while GPIO.input(self.RESET_BTN_PIN) == GPIO.LOW:
                    time.sleep(0.05)
            time.sleep(0.05)

    def handle_start_button(self):
        # Blue LED off, yellow LED on
        GPIO.output(self.BLUE_LED_PIN, GPIO.LOW)
        GPIO.output(self.YELLOW_LED_PIN, GPIO.HIGH)
        time.sleep(0.5)
        GPIO.output(self.GREEN_LED_PIN, GPIO.LOW)
        GPIO.output(self.RED_LED_PIN, GPIO.LOW)
        # Start test in a thread to avoid blocking
        threading.Thread(target=self.start_test, daemon=True).start()

    def handle_reset_button(self):
        # Turn off green/red, turn on blue, turn off yellow
        GPIO.output(self.GREEN_LED_PIN, GPIO.LOW)
        GPIO.output(self.RED_LED_PIN, GPIO.LOW)
        GPIO.output(self.YELLOW_LED_PIN, GPIO.LOW)
        GPIO.output(self.BLUE_LED_PIN, GPIO.HIGH)
        self.test_running = False

    def control_led(self, color):
        # Turn off all LEDs first
        GPIO.output(self.YELLOW_LED_PIN, GPIO.LOW)
        GPIO.output(self.GREEN_LED_PIN, GPIO.LOW)
        GPIO.output(self.RED_LED_PIN, GPIO.LOW)
        # Set LED based on color
        if color == "green":
            GPIO.output(self.GREEN_LED_PIN, GPIO.HIGH)
        elif color == "red":
            GPIO.output(self.RED_LED_PIN, GPIO.HIGH)
        elif color == "yellow":
            GPIO.output(self.YELLOW_LED_PIN, GPIO.HIGH)
        elif color == "blue":
            GPIO.output(self.BLUE_LED_PIN, GPIO.HIGH)
        # For debug
        print(f"LED status: blue={GPIO.input(self.BLUE_LED_PIN)}, yellow={GPIO.input(self.YELLOW_LED_PIN)}, green={GPIO.input(self.GREEN_LED_PIN)}, red={GPIO.input(self.RED_LED_PIN)}")

    def cleanup(self):
        GPIO.cleanup()

if __name__ == "__main__":
    try:
        app = BMSTestApp()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        app.cleanup()

# Mobile BMS ATP Check

## Overview

This program is designed to interface with a Battery Management System (BMS) to perform automated testing and validation during the final stages of battery manufacturing. It communicates with the BMS via serial commands, retrieves data from various registers, and verifies the integrity of the data. The results are logged and saved for further analysis.

---

## Features

### 1. Communication with BMS
- Establishes a serial connection with the BMS using configurable parameters (e.g., port, baud rate).
- Sends predefined commands to retrieve data from the BMS.

### 2. Data Retrieval
- Reads data from multiple registers, including:
  - **PIA**: Pack Information A (e.g., voltage, current, state of charge).
  - **PIB**: Pack Information B.
  - **PIC**: Pack Information C.
  - Alarm and fault conditions.
  - Basic and functional parameters.

### 3. Data Validation
- Verifies the integrity of the received data using CRC-16-CCITT checks.
- Parses the data into meaningful metrics such as voltage, current, temperature, and state of charge.

### 4. Logging and Reporting
- Saves the parsed data into a JSON file (`data/pack_info.json`).
- Logs any communication errors or anomalies for debugging.

---

## How It Works

### 1. Serial Communication
The program uses the `serial` library to establish a connection with the BMS. Commands are sent to the BMS, and responses are read back. Each response is validated using a CRC check to ensure data integrity.

### 2. Command Execution
The program sends a series of predefined commands to the BMS to retrieve data from various registers. Each command is appended with a CRC value for validation.

### 3. Data Parsing
The raw data received from the BMS is parsed into human-readable metrics. For example:
- Voltage is converted from raw bytes to volts.
- Temperature is converted from raw bytes to degrees Celsius.

### 4. Data Storage
The parsed data is saved as a JSON file in the `data/` directory for further analysis.

---

## File Structure

- **main.py**: The main script that handles communication with the BMS, data retrieval, and validation.
- **config.json**: Configuration file for the program.
- **data/**: Directory where the parsed data is saved.
- **Complete_Pack_Info_dump/**: Contains historical data for reference.
- **Test_Result_Dump_New/**: Stores test results for production units.

---

## How to Run

1. **Install Dependencies**:
   Ensure Python and the `pyserial` library are installed.

   ```bash
   pip install pyserial
   ```

2. **Connect the BMS**:
   Connect the BMS to the computer via a serial port.

3. **Run the Script**:
   Execute the `main.py` script to start the testing process.

   ```bash
   python main.py
   ```

4. **View Results**:
   The results will be saved in the `data/pack_info.json` file.

---

## Key Functions

### `BMSCommunicator`
- Handles serial communication with the BMS.
- Sends commands and reads responses.

### `send_command(command)`
- Sends a command to the BMS and reads the response.

### `check_crc(data)`
- Validates the integrity of the received data using CRC.

### `get_pack_info()`
- Retrieves data from the BMS and parses it into meaningful metrics.

### `save_to_json(data, filename)`
- Saves the parsed data into a JSON file.

---

## Example Output

A sample JSON output file (`data/pack_info.json`) might look like this:

```json
{
    "Acquire Device Manufacture Info": "Manufacturer XYZ",
    "PIA": {
        "Pack Voltage": 48.5,
        "Current": -2.3,
        "State of Charge (SOC)": 85.0,
        "State of Health (SOH)": 95.0
    },
    "PIB": {
        "Temperature": 25.3,
        "Cycle Count": 120
    },
    "PIC": {
        "Max Cell Voltage": 3.65,
        "Min Cell Voltage": 3.50
    },
    "Alarms": {
        "Overvoltage": false,
        "Undervoltage": false
    }
}
```

---

## Notes

- Ensure the BMS is powered on and properly connected before running the script.
- Modify the `port` and `baudrate` parameters in `main.py` if needed.
- The program is designed for production environments and includes robust error handling.

---

## Future Improvements

- Add support for additional BMS models.
- Integrate with a graphical user interface (GUI) for easier operation.
- Enhance logging and reporting features.
- Add type C panel mount connecter for charging

---

import streamlit as st
import json
import os
from main import BMSCommunicator

# Load test criteria from JSON file
def load_test_criteria():
    with open('config.json', 'r') as criteria_file:
        return json.load(criteria_file)

# Validate the test results against the criteria
def validate_results(pack_info):
    criteria = load_test_criteria()
    criteria['Acquire Device Manufacture Info']['BMS Serial Number'] = pack_info['Acquire Device Manufacture Info']['BMS Serial Number']
    
    errors = []  # List to hold error messages

    # Validate PIA
    for key, value in criteria['PIA'].items():
        if key in ['Raw Response', 'BMS Serial Number']:
            continue  # Skip these fields
        if isinstance(value, list):  # Range check
            if not (value[0] <= pack_info['PIA'][key] <= value[1]):
                errors.append(f"PIA {key} out of range: {pack_info['PIA'][key]} not in {value}")
        else:  # Exact match
            if pack_info['PIA'][key] != value:
                errors.append(f"PIA {key} mismatch: expected {value}, got {pack_info['PIA'][key]}")

    # Validate PIC
    for key, value in criteria['PIC'].items():
        if key in ['Raw Response']:  # Skip these fields in PIC
            continue
        if pack_info['PIC'][key] != value:
            errors.append(f"PIC {key} mismatch: expected {value}, got {pack_info['PIC'][key]}")

    return errors

def run_test(serial_number):
    bms = BMSCommunicator(port='/dev/ttyUSB0', baudrate=19200)
    pack_info = bms.get_pack_info()
    bms.save_to_json(pack_info, f'{serial_number}.json')  # Save JSON with serial number
    bms.close()
    
    # Validate results
    errors = validate_results(pack_info)
    if not errors:
        st.success("Test passed!")
    else:
        st.error("Test failed!\n" + "\n".join(errors))

    return pack_info

def load_json(serial_number):
    try:
        with open(f'{serial_number}.json', 'r') as json_file:
            return json.load(json_file)
    except FileNotFoundError:
        st.error("JSON file not found. Please run the test first.")
        return None

# Streamlit GUI
st.set_page_config(layout="wide")  # Set the layout to wide
# st.title("BMS Test Interface")

serial_number = st.text_input("Enter Serial Number:")

if st.button("Start Test", use_container_width=True):
    if serial_number:
        with st.spinner("Running test..."):
            pack_info = run_test(serial_number)
            st.success("Test completed!")

            # Create a fixed-height row
            row_height = 400  # Set the desired height in pixels
            st.markdown(
                f"""
                <div style="display: flex; height: {row_height}px;">
                    <div style="flex: 1; overflow-y: auto; padding: 10px;">
                        <h4>Pack Information</h4>
                        <p><strong>Manufacturer:</strong> {pack_info['Acquire Device Manufacture Info']['Manufacturer']}</p>
                        <p><strong>Device Name:</strong> {pack_info['Acquire Device Manufacture Info']['Device Name']}</p>
                        <p><strong>Firmware Version:</strong> {pack_info['Acquire Device Manufacture Info']['Firmware Version']}</p>
                        <p><strong>BMS Serial Number:</strong> {pack_info['Acquire Device Manufacture Info']['BMS Serial Number']}</p>
                        <p><strong>Pack Serial Number:</strong> {pack_info['Acquire Device Manufacture Info']['Pack Serial Number']}</p>
                    </div>
                    <div style="flex: 1; overflow-y: auto; padding: 10px;">
                        <h4>PIA Info</h4>
                        <p><strong>Pack Voltage:</strong> {pack_info['PIA']['Pack Voltage']} V</p>
                        <p><strong>Current:</strong> {pack_info['PIA']['Current']} A</p>
                        <p><strong>Remaining Capacity:</strong> {pack_info['PIA']['Remaining Capacity']} %</p>
                        <p><strong>Total Capacity:</strong> {pack_info['PIA']['Total Capacity']} Ah</p>
                        <p><strong>Total Discharge Capacity:</strong> {pack_info['PIA']['Total Discharge Capacity']} Ah</p>
                        <p><strong>SOC:</strong> {pack_info['PIA']['SOC']} %</p>
                        <p><strong>SOH:</strong> {pack_info['PIA']['SOH']} %</p>
                        <p><strong>Cycle:</strong> {pack_info['PIA']['Cycle']}</p>
                        <p><strong>Average Cell Voltage:</strong> {pack_info['PIA']['Average Cell Voltage']} V</p>
                        <p><strong>Average Cell Temperature:</strong> {pack_info['PIA']['Average Cell Temperature']} °C</p>
                        <p><strong>Max Cell Voltage:</strong> {pack_info['PIA']['Max Cell Voltage']} V</p>
                        <p><strong>Min Cell Voltage:</strong> {pack_info['PIA']['Min Cell Voltage']} V</p>
                        <p><strong>Max Cell Temperature:</strong> {pack_info['PIA']['Max Cell Temperature']} °C</p>
                        <p><strong>Min Cell Temperature:</strong> {pack_info['PIA']['Min Cell Temperature']} °C</p>
                        <p><strong>Max Discharge Current:</strong> {pack_info['PIA']['Max Discharge Current']} A</p>
                        <p><strong>Max Charge Current:</strong> {pack_info['PIA']['Max Charge Current']} A</p>
                    </div>
                    <div style="flex: 1; overflow-y: auto; padding: 10px;">
                        <h4>PIB Info</h4>
                        {''.join([f"<p><strong>Cell {i} Voltage:</strong> {pack_info['PIB'][f'Cell {i} Voltage']} V</p>" for i in range(1, 17)])}
                        <p><strong>Cell Temperature 1:</strong> {pack_info['PIB']['Cell Temperature 1']} °C</p>
                        <p><strong>Cell Temperature 2:</strong> {pack_info['PIB']['Cell Temperature 2']} °C</p>
                        <p><strong>Cell Temperature 3:</strong> {pack_info['PIB']['Cell Temperature 3']} °C</p>
                        <p><strong>Cell Temperature 4:</strong> {pack_info['PIB']['Cell Temperature 4']} °C</p>
                        <p><strong>Environment Temperature:</strong> {pack_info['PIB']['Environment Temperature']} °C</p>
                        <p><strong>Power Temperature:</strong> {pack_info['PIB']['Power Temperature']} °C</p>
                    </div>
                    <div style="flex: 1; overflow-y: auto; padding: 10px;">
                        <h4>PIC Info</h4>
                        <p><strong>System State Code:</strong> {pack_info['PIC']['System State Code']}</p>
                        <p><strong>FET Event Code:</strong> {pack_info['PIC']['FET Event Code']}</p>
                        <p><strong>Cell 08-01 Voltage Low Alarm State:</strong> {pack_info['PIC']['Cell 08-01 Voltage Low Alarm State']}</p>
                        <p><strong>Cell 16-09 Voltage Low Alarm State:</strong> {pack_info['PIC']['Cell 16-09 Voltage Low Alarm State']}</p>
                        <p><strong>Cell 08-01 Voltage High Alarm State:</strong> {pack_info['PIC']['Cell 08-01 Voltage High Alarm State']}</p>
                        <p><strong>Cell 16-09 Voltage High Alarm State:</strong> {pack_info['PIC']['Cell 16-09 Voltage High Alarm State']}</p>
                        <p><strong>Cell 08-01 Temperature Low Alarm State:</strong> {pack_info['PIC']['Cell 08-01 Temperature Low Alarm State']}</p>
                        <p><strong>Cell 16-09 Temperature Low Alarm State:</strong> {pack_info['PIC']['Cell 16-09 Temperature Low Alarm State']}</p>
                        <p><strong>Battery Equalization State Code:</strong> {pack_info['PIC']['Battery Equalization State Code']}</p>
                        <p><strong>Hard Fault Event Code:</strong> {pack_info['PIC']['Hard Fault Event Code']}</p>
                        <p><strong>Voltage Event Code:</strong> {pack_info['PIC']['Voltage Event Code']}</p>
                        <p><strong>Cells Temperature Event Code:</strong> {pack_info['PIC']['Cells Temperature Event Code']}</p>
                        <p><strong>Environment and Power Temperature Event Code:</strong> {pack_info['PIC']['Environment and Power Temperature Event Code']}</p>
                        <p><strong>Current Event Code 1:</strong> {pack_info['PIC']['Current Event Code 1']}</p>
                        <p><strong>Current Event Code 2:</strong> {pack_info['PIC']['Current Event Code 2']}</p>
                        <p><strong>Residual Capacity Code:</strong> {pack_info['PIC']['Residual Capacity Code']}</p>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Reset button at the bottom of the page
            if st.button("Reset", use_container_width=True):
                st.rerun()  # Reset the app for the next test 
    else:
        st.error("Please enter a serial number.")
    
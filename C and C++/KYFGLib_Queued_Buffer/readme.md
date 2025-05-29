# KYFGLib_Queued_Buffer

This C project demonstrates how to use the Vision Point API to update firmware for KAYA Instruments PCIe devices. 

## Features

- Scans and connects to available KAYA Instruments PCIe devices.
- Validates firmware file.
- Writes firmware.
- Validates written firmware.

## Requirements

- Vision Point API (KYFGLib) library installed.
- KAYA Instruments PCIe device.

## Build and Run

1. Ensure the **KYFGLib** headers and libraries are accessible.
2. Compile the project:
   - On Linux:
     ```bash
	 make
     ```
   - On Windows:
     Build with Microsoft Visual Studio (v141).

3. Run the program:
   - On Linux:
  ```bash
  ./KYFGLib_Example_Firmware_update
     ```
   - On Windows:
	 Run it under Release x64 solution.
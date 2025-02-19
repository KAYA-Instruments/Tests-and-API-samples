# Common KAYA imports DO NOT EDIT!!!
import sys
import os
import argparse
sys.path.insert(0, os.environ['KAYA_VISION_POINT_PYTHON_PATH'])
from KYFGLib import *

# Common Case imports DO NOT EDIT!!!
from enum import IntEnum  # for CaseReturnCode

# additional imports required by particular case, ADD CASE SPECIFIC IMPORTS UNDER THIS LINE:
import threading
import time
import pathlib


def CaseArgumentParser():
    parser = argparse.ArgumentParser()
    # Common arguments for all cases DO NOT EDIT!!!
    parser.add_argument('--unattended', default=False, action='store_true', help='Do not interact with user')
    parser.add_argument('--no-unattended', dest='unattended', action='store_false')
    parser.add_argument('--deviceList', default=False, action='store_true',
                        help='Print list of available devices and exit')
    parser.add_argument('--deviceIndex', type=int, default=-1,
                        help='Index of PCI device to use, '
                             'run this script with "--deviceList" to see available devices and exit')
    # Other arguments needed for this specific case, PARSE CASE SPECIFIC ARGUMENTS UNDER THIS LINE:

    return parser

def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)
gIsTestPassed = True
gFirstProcessFlag = False
class UpdateStruct:
    def __init__(self):
        self.counter = 0
        self.run_process = False
        return
def check_update_file(handle, file, silent=False):
    try:
        (status, flashMinorRev, flashMajorRev, fileMinorRev, fileMajorRev, flashVendorId, flashBoardId,
         fileVendorId, fileBoardId, flashVersionPath, flashTimeStamp, fileVersionPath,
         fileTimeStamp) = KYFG_CheckUpdateFile(handle, file)
        if not silent:
            print('File successfully checked')
            print(f"flashMinorRev = {flashMinorRev}")
            print(f"flashMajorRev = {flashMajorRev}")
            print(f"fileMinorRev = {fileMinorRev}")
            print(f"fileMajorRev = {fileMajorRev}")
            print(f"flashVendorId = {flashVendorId}")
            print(f"flashBoardId = {flashBoardId}")
            print(f"fileVendorId = {fileVendorId}")
            print(f"fileBoardId = {fileBoardId}")
            print(f"flashVersionPath = {flashVersionPath}")
            print(f"flashTimeStamp = {flashTimeStamp}")
            print(f"fileVersionPath = {fileVersionPath}")
            print(f"fileTimeStamp = {fileTimeStamp}")
        return True
    except Exception as e:
        print("You can't to update firmware with this file")
        print(type(e), str(e))
        return False
def startFirmwareUpdate(handle, file, function, object):
    try:
        (status,) = KYFG_LoadFirmware(handle, file, function, py_object(object))
        return True
    except Exception as e:
        print(type(e), str(e))
        print('Firmware update failed')
        return False
def find_bin_file(handle, folder: pathlib.Path):
    for next_file in folder.iterdir():
        if next_file.name.endswith('.bin') and check_update_file(handle, next_file.as_posix()):
            return next_file
def firstCallbackFunction(updateStatus, userContext):
    update_struct = cast(userContext, py_object).value
    if updateStatus.link_mask >= updateStatus.link_speed*0.8 or not updateStatus.is_writing:
        update_struct.run_process = False
    update_struct.counter += 1
    print("\n\nFIRST PROCESS CALLBACK FUNCTION")
    print(f'RUN update {update_struct.run_process}')
    print(f'CALLBACK number {update_struct.counter}')
    print(f'struct_version {updateStatus.struct_version}')
    print(f'Bytes already sent {updateStatus.link_mask}')
    print(f'Firmware file size {updateStatus.link_speed}')
    print(f"{'writing new firmware' if updateStatus.is_writing else 'validating new firmware'}\n")
def secondCallbackFunction(updateStatus, userContext):
    global gIsTestPassed
    gIsTestPassed = False
    update_struct = cast(userContext, py_object).value
    update_struct.counter += 1
    print(f"\n\n{'*'*32}WARNING!!! SECOND PROCESS MUST BE FAILED {'*'*32}")
    print("Seconf PROCESS CALLBACK FUNCTION")
    print(f'CALLBACK number {update_struct.counter}')
    print(f'struct_version {updateStatus.struct_version}')
    print(f'Bytes already sent {updateStatus.link_mask}')
    print(f'Firmware file size {updateStatus.link_speed}')
    print(f"{'writing new firmware' if updateStatus.is_writing else 'validating new firmware'}\n")
def CaseRun(args):
    print(f'\nEntering CaseRun({args}) (use -h or --help to print available parameters and exit)...')

    device_infos = {}

    # Start of common KAYA prolog for 'def CaseRun(args)'
    unattended = args["unattended"]
    device_index = args["deviceIndex"]

    class CaseReturnCode(IntEnum):
        SUCCESS = 0
        COULD_NOT_RUN = 1
        NO_HW_FOUND = 2
        NO_REQUIRED_PARAM = 3
        WRONG_PARAM_VALUE = 4

    # Find and print list of available devices
    (status, infosize_test) = KY_DeviceScan()
    for x in range(0, infosize_test):
        (status, device_infos[x]) = KY_DeviceInfo(x)
        dev_info = device_infos[x]
        print(f'Found device [{x}]: "{dev_info.szDeviceDisplayName}"')

    # If only print of available devices list was requested
    if args["deviceList"]:
        return CaseReturnCode.SUCCESS  # we are done

    # deviceIndex == -1 means we need to ask user
    if device_index < 0:
        # Ask user what device to use for this test
        # in unattended mode, use the first device detected in the system (index 0)
        if unattended:
            device_index = 0
            print(f'\n!!! deviceIndex {device_index} forcibly selected in unattended mode !!!')
        else:
            device_index = int(input(f'Select PCI device to use (0 ... {infosize_test - 1})'))
            print(f'\ndeviceIndex {device_index} selected')

    # Verify deviceIndex being in the allowed range
    if device_index >= infosize_test:
        print(f'\nDevice with the index {device_index} does not exist, exiting...')
        return CaseReturnCode.NO_HW_FOUND

    # End of common KAYA prolog for "def CaseRun(args)"
    # Find the bin file
    global gIsTestPassed
    (firstGrabberHandle,) = KYFG_Open(device_index)
    (secondGrabberHandle,) = KYFG_Open(device_index)
    bin_folder = pathlib.Path(__file__).parent
    bin_file = find_bin_file(secondGrabberHandle, bin_folder)
    print(f'BIN file is {bin_file}')
    if not bin_file:
        return CaseReturnCode.NO_HW_FOUND
    first_update_obj = UpdateStruct()
    second_update_obj = UpdateStruct()
    first_update_thread = threading.Thread(target=startFirmwareUpdate, args=(firstGrabberHandle, bin_file.as_posix(),
                                                                              firstCallbackFunction, first_update_obj))
    first_update_obj.run_process = True
    first_update_thread.start()
    time.sleep(5)
    print("Trying to run second process")
    is_updated = startFirmwareUpdate(secondGrabberHandle, bin_file.as_posix(), secondCallbackFunction,
                                     second_update_obj)
    while first_update_obj.run_process:
        is_updated = startFirmwareUpdate(secondGrabberHandle, bin_file.as_posix(), secondCallbackFunction, second_update_obj)
        if is_updated:
            gIsTestPassed = False
            print(f"{'*'*32}SECOND UPDATE WAS PERFORMED{'*'*32}")
        else:
            print(f"{'*'*32}SECOND UPDATE WAS FAILED{'*'*32}")
        time.sleep(10)
    first_update_thread.join()
    assert gIsTestPassed, f"\n{'*'*84}\n{'*'*32}\tTEST FAILED\t\t{'*'*32}\n{'*'*84}"

    (status,) = KYFG_Close(firstGrabberHandle)
    (status,) = KYFG_Close(secondGrabberHandle)

    print(f'\nExiting from CaseRun({args}) with code SUCCESS...')
    return CaseReturnCode.SUCCESS


# The flow starts here
if __name__ == "__main__":
    try:
        args_ = ParseArgs()
        return_code = CaseRun(args_)
        print(f'Case return code: {return_code}')
    except Exception as ex:
        print(f"Exception of type {type(ex)} occurred: {str(ex)}")
        exit(-200)

    exit(return_code)

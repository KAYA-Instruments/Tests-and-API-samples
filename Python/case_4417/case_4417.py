# Common KAYA imports DO NOT EDIT!!!
import sys
import os
import argparse
sys.path.insert(0, os.environ['KAYA_VISION_POINT_PYTHON_PATH'])
from KYFGLib import *

# Common Case imports DO NOT EDIT!!!
from enum import IntEnum  # for CaseReturnCode

# additional imports required by particular case, ADD CASE SPECIFIC IMPORTS UNDER THIS LINE:
import time
import pathlib
import platform
import subprocess


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
    parser.add_argument("--firstConnectionConfigDefault", type=str, default="x1_CXP_12")
    parser.add_argument("--secondConnectionConfigDefault", type=str, default="x1_CXP_3")

    return parser

def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)

def openAllCameras(cameraList:list, connectionConfig):
    for camHandle in cameraList:
        (status, camInfo) = KYFG_CameraInfo2(camHandle)
        try:
            (status) = KYFG_CameraOpen2(camHandle,None)
        except Exception as e:
            print(f"camera {camInfo.deviceModelName} failed to open")
            print(type(e), str(e))
            continue
        if connectionConfig is not None:
            KYFG_SetCameraValueEnum_ByValueName(camHandle, "ConnectionConfigDefault", connectionConfig)
            print(f"Set connection config to {connectionConfig}")
        print(f"camera {camInfo.deviceModelName} successfully opened")

def closeAllCameras(cameraList:list):
    for camHandle in cameraList:
        (status, camInfo) = KYFG_CameraInfo2(camHandle)
        try:
            (status) = KYFG_CameraClose(camHandle)
        except Exception as e:
            print(f"camera {camInfo.deviceModelName} failed to close")
            print(type(e), str(e))
            continue
        print(f"camera {camInfo.deviceModelName} successfully closed")

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

    firstConnectionConfigDefault = args["firstConnectionConfigDefault"]
    secondConnectionConfigDefault = args["secondConnectionConfigDefault"]
    (grabberHandle,) = KYFG_Open(device_index)
    (status, cameraList) = KYFG_UpdateCameraList(grabberHandle)
    assert len(cameraList)>=2, "Should be 2 and more cameras on grabber"
    openAllCameras(cameraList, firstConnectionConfigDefault)
    closeAllCameras(cameraList)
    openAllCameras(cameraList, None)
    for cameraHandle in cameraList:
        (status, camInfo) = KYFG_CameraInfo2(cameraHandle)
        KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "ConnectionConfigDefault", secondConnectionConfigDefault)
        print(f"Connection config default set to {secondConnectionConfigDefault} on camera {camInfo.deviceModelName}")
    closeAllCameras(cameraList)
    (status, cameraList2) = KYFG_UpdateCameraList(grabberHandle)
    assert len(cameraList) == len(cameraList2), "Error while second detection"
    openAllCameras(cameraList2, None)
    isTestPassed = True
    for cameraHandle in cameraList:
        (status, camInfo) = KYFG_CameraInfo2(cameraHandle)
        (status, connectionConfigDefault) = KYFG_GetCameraValueStringCopy(cameraHandle, "ConnectionConfigDefault")
        (status, connectionConfig) = KYFG_GetCameraValueStringCopy(cameraHandle, "ConnectionConfig")
        print(f"\nResults on camera: {camInfo.deviceModelName}")
        print(f"get connectionConfig = {connectionConfig}")
        print(f"get connectionConfigDefault = {connectionConfigDefault}")
        if connectionConfigDefault != secondConnectionConfigDefault or secondConnectionConfigDefault != connectionConfig:
            print("test Failed")
            isTestPassed = False
        KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "ConnectionConfigDefault", "x1_CXP_12")

    closeAllCameras(cameraList2)
    KYFG_Close(grabberHandle)
    assert isTestPassed, "Test failed"
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

# Common KAYA imports DO NOT EDIT!!!
import sys
import os
import argparse
sys.path.insert(0, os.environ['KAYA_VISION_POINT_PYTHON_PATH'])
from KYFGLib import *

# Common Case imports DO NOT EDIT!!!
from enum import IntEnum  # for CaseReturnCode

# additional imports required by particular case, ADD CASE SPECIFIC IMPORTS UNDER THIS LINE:
import subprocess


def CaseArgumentParser():
    parser = argparse.ArgumentParser()

    # Common arguments for all cases DO NOT EDIT!!!
    parser.add_argument('--unattended', default=False, action='store_true', help='Do not interact with user')
    parser.add_argument('--no-unattended', dest='unattended', action='store_false')
    parser.add_argument('--deviceList', default=False, action='store_true',
                        help='Print list of available devices and exit')
    parser.add_argument('--deviceIndex', type=int, default=-1,
                        help='Index of PCI device to use, run this script with "--deviceList" to see available devices')
    # Other arguments needed for this specific case, PARSE CASE SPECIFIC ARGUMENTS UNDER THIS LINE:
    return parser

DeviceInfos = {}
camHandleArray = {}


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

    # Open selected PCI device
    (status, device_info) = KY_DeviceInfo(device_index)
    if device_info.m_Protocol != KY_DEVICE_PROTOCOL.KY_DEVICE_PROTOCOL_CoaXPress:
        return CaseReturnCode.COULD_NOT_RUN
    (grabberHandle,) = KYFG_Open(device_index)

    (CameraScan_status, camHandleArray[device_index]) = KYFG_UpdateCameraList(grabberHandle)
    cams_num = len(camHandleArray[device_index])
    print(f"Found {cams_num} cameras")

    if not cams_num:
        print("\nRequired hardware not found ")
        return -102

    KYFG_Close(grabberHandle)
    for i in range(cams_num):
        (grabberHandle,) = KYFG_Open(device_index)
        (CameraScan_status, camHandleArray[device_index]) = KYFG_UpdateCameraList(grabberHandle)
        cameraHandle = camHandleArray[device_index][i]
        KYFG_CameraOpen2(cameraHandle, None)
        # Getting value of 'ConnectionConfig'
        (_, camera_connection_config_value) = KYFG_GetCameraValueEnum(cameraHandle, "ConnectionConfig")
        (Status, camInfo) = KYFG_CameraInfo2(cameraHandle)
        cameraName = camInfo.deviceModelName
        # Setting value of 'CameraSelector'
        KYFG_SetGrabberValueInt(grabberHandle, "CameraSelector", i)
        # Getting value of 'LinksConnectionMask'
        (status, value) = KYFG_GetGrabberValueStringCopy(grabberHandle, "LinksConnectionMask")
        linksList = list(value)
        grabberLinks = []
        cameraLinks = []
        for j in range(len(linksList)):
            if linksList[j] != '-':
                grabberLinks.append(j)
                cameraLinks.append(int(linksList[j]))
        KYFG_CameraClose(cameraHandle)
        KYFG_Close(grabberHandle)

        (grabberHandle,) = KYFG_Open(device_index)
        # Setting value of 'CameraSelector'
        KYFG_SetGrabberValueInt(grabberHandle, "CameraSelector", i)
        # Setting value of 'ManualCameraMode'
        KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "ManualCameraMode", "On")
        # Setting value of 'ManualCameraConnectionConfig'
        KYFG_SetGrabberValueEnum(grabberHandle, "ManualCameraConnectionConfig", camera_connection_config_value)
        # Setting value of 'ManualCameraChannelSelector'
        for x in range(len(grabberLinks)):
            KYFG_SetGrabberValueEnum(grabberHandle, "ManualCameraChannelSelector", cameraLinks[x])
        # Setting value of 'ManualCameraFGLink'
            KYFG_SetGrabberValueInt(grabberHandle, "ManualCameraFGLink", grabberLinks[x])
        # Manual detection
        (CameraScan_status, camHandleArray[device_index]) = KYFG_UpdateCameraList(grabberHandle)
        cameraHandle = camHandleArray[device_index][0]
        KYFG_CameraOpen2(cameraHandle, None)
        (Status, camInfo) = KYFG_CameraInfo2(cameraHandle)
        print(f"Camera {camInfo.deviceModelName} status is opened")
        # Check if correct camera was opened
        assert cameraName == camInfo.deviceModelName, 'Wrong camera is opened'
        KYFG_CameraClose(cameraHandle)
        KYFG_Close(grabberHandle)
    print(f'\nExiting from CaseRun({args}) with code 0...')
    return CaseReturnCode.SUCCESS


def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)


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

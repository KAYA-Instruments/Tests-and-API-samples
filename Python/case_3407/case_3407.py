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
    (grabberHandle,) = KYFG_Open(device_index)
    (status, camList) = KYFG_UpdateCameraList(grabberHandle)
    error_count = 0
    for i in range(len(camList)):
        cameraHandle = camList[i]
        expected_LinksConnectionMask = ''
        (status, camInfo) = KYFG_CameraInfo2(cameraHandle)
        print(f"\n{camInfo.deviceModelName}")
        print("master_link", camInfo.master_link)
        print("link_mask bin", str(bin(camInfo.link_mask)))
        bin_str_big_endian = str(bin(camInfo.link_mask))[: str(bin(camInfo.link_mask)).index('b'):-1]
        (status,) = KYFG_CameraOpen2(cameraHandle, None)
        KYFG_SetGrabberValueInt(grabberHandle, "CameraSelector", i)
        (status, LinksConnectionMask) = KYFG_GetGrabberValueStringCopy(grabberHandle, "LinksConnectionMask")
        for i in range(len(bin_str_big_endian)):
            if bin_str_big_endian[i] == "0":
                expected_LinksConnectionMask += '-'
            elif bin_str_big_endian[i] == "1" and camInfo.master_link == i:
                expected_LinksConnectionMask += '0'
            elif bin_str_big_endian[i] == "1" and camInfo.master_link != i:
                expected_LinksConnectionMask += "1"
        for i in range(len(LinksConnectionMask) - len(expected_LinksConnectionMask)):
            expected_LinksConnectionMask += '-'
        print("expected_LinksConnectionMask", expected_LinksConnectionMask)
        print("LinksConnectionMask", LinksConnectionMask)
        (status,) = KYFG_CameraClose(cameraHandle)
        if expected_LinksConnectionMask != LinksConnectionMask:
            print('Error while test')
            error_count += 1
    (status,) = KYFG_Close(grabberHandle)
    assert error_count == 0, 'Test not Passed'

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

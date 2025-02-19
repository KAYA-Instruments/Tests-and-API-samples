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

camHandleArray = {}
camHandleArray2 = {}


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
    parser.add_argument('--chameleonDeviceIndex', type=int, default=1,
                        help='Index of Chameleon device to use')
    parser.add_argument('--camera', type=str, default='Chameleon',
                        help='Chameleon deviceModelName')
    parser.add_argument('--suffixFalse', type=str, default='')

    return parser


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
    (status, device_info) = KY_DeviceInfo(device_index)
    if device_info.m_Protocol != KY_DEVICE_PROTOCOL.KY_DEVICE_PROTOCOL_CoaXPress:
        print('Test could not run on this grabber')
        return CaseReturnCode.COULD_NOT_RUN
    (grabberHandle,) = KYFG_Open(device_index)
    # Update Chameleon device camera list and open chameleon
    print('First device scan')
    (CameraScan_status, camHandleArray) = KYFG_UpdateCameraList(grabberHandle)

    if len(camHandleArray)==0:
        print('No cameras on this FG')
        return CaseReturnCode.NO_HW_FOUND
    is_chameleon_exist = False
    for cameraHandle in camHandleArray:
        (Status, camInfo) = KYFG_CameraInfo2(cameraHandle)
        if 'Chameleon' in camInfo.deviceModelName:
            is_chameleon_exist=True
            KYFG_CameraOpen2(cameraHandle, None)
            print(f'Camera {camInfo.deviceModelName} is open')
    if not is_chameleon_exist:
        print ('Chameleon doesn\'t detected')
        return CaseReturnCode.NO_HW_FOUND

    # Update PCI device camera list again
    print('Second device scan')
    (CameraScan_status, camHandleArray) = KYFG_UpdateCameraList(grabberHandle)


    is_chameleon_exist = False
    for cameraHandle in camHandleArray:
        (Status, camInfo) = KYFG_CameraInfo2(cameraHandle)
        if 'Chameleon' in camInfo.deviceModelName:
            print('Chameleon in the camera list')
            is_chameleon_exist = True
            break
    assert is_chameleon_exist, 'Chameleon doesn\'t detected'

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

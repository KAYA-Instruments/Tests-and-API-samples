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
    parser.add_argument('--numberOfTests', type=int, default=10)
    parser.add_argument('--numberOfFrames',type=int, default=10)
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

    #Receive and parse all external parameters
    number_of_tests = args["numberOfTests"]
    number_of_frames = args["numberOfFrames"]
    #Open frame grabber
    (device_handle,) = KYFG_Open(device_index)
    device_info = device_infos[device_index]
    print(
        f'Opened device [{device_index}]: (PCI {device_info.nBus}:{device_info.nSlot}:{device_info.nFunction})"{device_info.szDeviceDisplayName}"')
    for test in range(number_of_tests):
        print(f'Test number {test+1}')
        # Perform camera scan
        (status, camHandleArray_col) = KYFG_UpdateCameraList(device_handle)
        print(f'Camera scan result:\nStatus: {status}\nCamHandleArray: {camHandleArray_col}')
        assert len(camHandleArray_col) != 0, 'Thera is no cameras on this grabber'
        #All the detected cameras start streaming with the "number_of_frames"
        for camHandle in camHandleArray_col:
            open_cam_status = KYFG_CameraOpen2(camHandle, None)
            try:
                if KYFG_IsGrabberValueImplemented(grabberHandle, 'TriggerMode'):
                    KYFG_SetGrabberValueEnum(grabberHandle, "TriggerMode", 0)
                if KYFG_IsCameraValueImplemented(cameraHandle, "TriggerMode"):
                    KYFG_SetCameraValueEnum(cameraHandle, "TriggerMode", 0)
            except:
                pass
            print(f'camera {camHandle} is open. Status: {open_cam_status}')
            (stream_status, stream_handle) = KYFG_StreamCreateAndAlloc(camHandle, number_of_frames,0)
            print(f'Created stream: status: {stream_status}, handle: {stream_handle}')
            (status,) = KYFG_CameraStart(camHandle,stream_handle,number_of_frames)
            time.sleep(1)
            (status,) = KYFG_CameraStop(camHandle)
            (delete_stram_status,) = KYFG_StreamDelete(stream_handle)
            print(f'Deleted stream: status: {delete_stram_status}, handle: {stream_handle}')
            close_cam_status = KYFG_CameraClose(camHandle)
            print(f'Camera{camHandle} is close, status: {close_cam_status}')

    KYFG_Close(device_handle)
    print(f'\nExiting from CaseRun({args}) with code 0...')
    return CaseReturnCode.SUCCESS



if __name__ == "__main__":
    try:
        args_ = ParseArgs()
        return_code = CaseRun(args_)
    except Exception as ex:
        print(f"Exception of type {type(ex)} occurred: {str(ex)}")
        exit(-200)

    exit(return_code)
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
    parser.add_argument('--iterations', type=int, default=10, help='Number of iteration for test')

    return parser

def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)

class StreamInfoStruct:
    def __init__(self):
        self.callbackCount = 0
        return

def Stream_callback_func(buffHandle, userContext):
    if (buffHandle == 0):
        return

    userContext.callbackCount += 1
    return

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
    iterations = args['iterations']
    (grabberHandle,) = KYFG_Open(device_index)
    (status, cameraList) = KYFG_UpdateCameraList(grabberHandle)
    print(f'Found {len(cameraList)} cameras')
    if len(cameraList) == 0:
        print('There is no cameras on this grabber')
        return CaseReturnCode.NO_HW_FOUND
    error_count = 0
    for cameraHandle in cameraList:
        (status, camInfo) = KYFG_CameraInfo2(cameraHandle)
        (status,) = KYFG_CameraOpen2(cameraHandle,None)
        try:
            if KYFG_IsGrabberValueImplemented(grabberHandle, 'TriggerMode'):
                KYFG_SetGrabberValueEnum(grabberHandle, "TriggerMode", 0)
            if KYFG_IsCameraValueImplemented(cameraHandle, "TriggerMode"):
                KYFG_SetCameraValueEnum(cameraHandle, "TriggerMode", 0)
        except:
            pass
        print(f'\nCamera {camInfo.deviceModelName} is open')
        (status, streamHandle) = KYFG_StreamCreateAndAlloc(cameraHandle, 16, 0)
        streamInfoStruct = StreamInfoStruct()
        (status,) = KYFG_StreamBufferCallbackRegister(streamHandle, Stream_callback_func, streamInfoStruct)
        duration = 1
        (status, fps) = KYFG_GetCameraValueFloat(cameraHandle, "AcquisitionFrameRate")
        if fps < 5:
            duration = 2
        elif fps > 15:
            duration = 0.5
        for i in range(iterations):
            current_counter = streamInfoStruct.callbackCount
            print(f'Test number {i + 1} from {iterations}')
            (status,) = KYFG_CameraStart(cameraHandle, streamHandle, 0)
            time.sleep(duration)
            (status,) = KYFG_CameraStop(cameraHandle)
            (status, frame_counter) = KYFG_GetGrabberValueInt(grabberHandle, "RXFrameCounter")
            (status, drop_counter) = KYFG_GetGrabberValueInt(grabberHandle, "DropFrameCounter")
            if current_counter > streamInfoStruct.callbackCount or frame_counter == 0 != drop_counter:
                print(f'Incorrect acquisition:\nCurrent_counter = {current_counter}')
                print(f'CallbackCount = {streamInfoStruct.callbackCount}')
                print(f'Frame_counter = {frame_counter}\nDrop_counter = {drop_counter}')
                error_count += 1
                break
        print(f'Results on camera {camInfo.deviceModelName}')
        print(f'CallbackCount = {streamInfoStruct.callbackCount}')
        (status,) = KYFG_StreamBufferCallbackUnregister(streamHandle, Stream_callback_func)
        (status,) = KYFG_StreamDelete(streamHandle)
        (status,) = KYFG_CameraClose(cameraHandle)
    (status,) = KYFG_Close(grabberHandle)
    assert error_count == 0, 'There are errors while test'
    print(f'\nExiting from CaseRun({args}) with code 0...')
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

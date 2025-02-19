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
import math


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

class StreamInfoStruct:
    def __init__(self):
        self.callbackCount = 0
        self.instantsFps = []
        self.timestamps = []
        return

def Stream_callback_func(buffHandle, userContext):

    if buffHandle == 0:
        return
    userContext.callbackCount += 1
    (KYFG_BufferGetInfo_status, pInfoFPS, pInfoSize, pInfoType) = KYFG_BufferGetInfo(
        buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_INSTANTFPS)
    (KYFG_BufferGetInfo_status, timestamp, pInfoSize, pInfoType) = KYFG_BufferGetInfo(
        buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_TIMESTAMP)

    userContext.instantsFps.append(pInfoFPS)
    userContext.timestamps.append(timestamp)
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
    (grabberHandle,) = KYFG_Open(device_index)
    (status, cameraList) = KYFG_UpdateCameraList(grabberHandle)
    print(f'Found {len(cameraList)} cameras')
    if len(cameraList) == 0:
        print('There are no cameras on this grabber')
        return CaseReturnCode.NO_HW_FOUND
    error_count = 0
    for cameraHandle in cameraList:
        (status, camInfo) = KYFG_CameraInfo2(cameraHandle)
        (status,) = KYFG_CameraOpen2(cameraHandle, None)
        try:
            if KYFG_IsGrabberValueImplemented(grabberHandle, 'TriggerMode'):
                KYFG_SetGrabberValueEnum(grabberHandle, "TriggerMode", 0)
            if KYFG_IsCameraValueImplemented(cameraHandle, "TriggerMode"):
                KYFG_SetCameraValueEnum(cameraHandle, "TriggerMode", 0)
        except:
            pass
        print(f'\nCamera {camInfo.deviceModelName} is open')
        if 'Iron' in camInfo.deviceModelName:
            (status, maxFps) = KYFG_GetCameraValueFloat(cameraHandle, "AcquisitionFrameRateMax")
            (status,) = KYFG_SetCameraValueFloat(cameraHandle, "AcquisitionFrameRate", float(math.floor(maxFps)))
        elif 'Adimec' in camInfo.deviceVendorName:
            (status,) = KYFG_CameraExecuteCommand(cameraHandle, "AcquisitionMaxFrameRate")
            (status, maxFps) = KYFG_GetCameraValueFloat(cameraHandle, "AcquisitionFrameRate")
        elif "Chameleon" in camInfo.deviceModelName:
            KYFG_SetCameraValueFloat(cameraHandle, "AcquisitionFrameRate", 400.0)
        (status, streamHandle) = KYFG_StreamCreateAndAlloc(cameraHandle, 16, 0)
        streamStruct = StreamInfoStruct()
        (status,) = KYFG_StreamBufferCallbackRegister(streamHandle, Stream_callback_func, streamStruct)
        (status,) = KYFG_CameraStart(cameraHandle, streamHandle, 0)
        time.sleep(3)
        (status,) = KYFG_CameraStop(cameraHandle)
        streamStruct.instantsFps.pop(0)
        instant_fps = sum(streamStruct.instantsFps)/len(streamStruct.instantsFps)
        KYFG_SetGrabberValueInt(grabberHandle, "CameraSelector", cameraList.index(cameraHandle))
        (status, frame_counter) = KYFG_GetGrabberValueInt(grabberHandle, "RXFrameCounter")
        (status, drop_frame_counter) = KYFG_GetGrabberValueInt(grabberHandle, "DropFrameCounter")
        timestamp = int(streamStruct.timestamps[0]+1e+9)
        frames_capture_in_sec = 0
        for i in streamStruct.timestamps:
            if i >= timestamp:
                frames_capture_in_sec = streamStruct.timestamps.index(i)-1  # "-1" because we drop first and last frame
                break
        print('frames_capture_in_sec', frames_capture_in_sec)
        print('instant_fps', round(instant_fps, 3))
        print('drop_frame_counter', drop_frame_counter)
        (status,) = KYFG_CameraClose(cameraHandle)
        if drop_frame_counter != 0 or abs(instant_fps - frames_capture_in_sec) > 1.5:
            print(f"Test NOT pass for camera {camInfo.deviceModelName}\n")
            error_count += 1
        else: print(f"Test pass for camera {camInfo.deviceModelName}\n")

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
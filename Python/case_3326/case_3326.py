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
    parser.add_argument('--iterations', type=int, default=10, help='Number of test for each camera')

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
    iterations = args['iterations']
    (grabberHandle,) = KYFG_Open(device_index)
    (status, cameraList) = KYFG_UpdateCameraList(grabberHandle)
    print(f'Found {len(cameraList)} cameras')
    if len(cameraList) == 0:
        print('There is no cameras on this list')
        return CaseReturnCode.NO_HW_FOUND
    error_count = 0
    for cameraHandle in cameraList:
        (status,) = KYFG_CameraOpen2(cameraHandle, None)
        try:
            if KYFG_IsGrabberValueImplemented(grabberHandle, 'TriggerMode'):
                KYFG_SetGrabberValueEnum(grabberHandle, "TriggerMode", 0)
            if KYFG_IsCameraValueImplemented(cameraHandle, "TriggerMode"):
                KYFG_SetCameraValueEnum(cameraHandle, "TriggerMode", 0)
            if KYFG_IsCameraValueImplemented(cameraHandle, "SimulationTriggerMode"):
                KYFG_SetCameraValueEnum(cameraHandle, "SimulationTriggerMode", 0)
        except:
            pass
        (status, camInfo) = KYFG_CameraInfo2(cameraHandle)
        print(f'Camera {camInfo.deviceModelName} is open')
        (status,) = KYFG_SetGrabberValueInt(grabberHandle, "CameraSelector", cameraList.index(cameraHandle))
        (status,) = KYFG_SetGrabberValueEnum(grabberHandle, "TransferControlMode", 1)
        (status, streamHandle) = KYFG_StreamCreateAndAlloc(cameraHandle,16,0)
        (status, frame_counter) = KYFG_GetGrabberValueInt(grabberHandle, "RXFrameCounter")
        (status, drop_frame_counter) = KYFG_GetGrabberValueInt(grabberHandle, "DropFrameCounter")
        if frame_counter != 0 or drop_frame_counter != 0:
            print(f'\nErrors on camera {camInfo.deviceModelName}:')
            print(f'frame_counter = {frame_counter}')
            print(f'drop_frame_counter = {drop_frame_counter}')
            error_count+=1
        duration = 1
        (status, fps) = KYFG_GetCameraValueFloat(cameraHandle, "AcquisitionFrameRate")
        if fps<5:
            duration = 2
        elif fps < 10:
            duration = 1
        else:
            duration = 0.5
        (status,) = KYFG_CameraStart(cameraHandle, streamHandle, 0)
        time.sleep(duration)
        (status, frame_counter) = KYFG_GetGrabberValueInt(grabberHandle, "RXFrameCounter")
        if frame_counter != 0:
            print(f'\n ERROR on camera {camInfo.deviceModelName}: \nStart acquisition before execute command:')
            print(f'frame_counter = {frame_counter}')
            print(f'drop_frame_counter = {drop_frame_counter}')
            error_count += 1
            (status,) = KYFG_CameraStop(cameraHandle)
            (status,) = KYFG_StreamDelete(streamHandle)
            (status,) = KYFG_SetGrabberValueEnum(grabberHandle, "TransferControlMode", 0)
            continue
        for i in range(iterations):
            (status,) = KYFG_CameraExecuteCommand(cameraHandle, "AcquisitionStart")
            time.sleep(duration)
            (status,) = KYFG_CameraExecuteCommand(cameraHandle, "AcquisitionStop")
            (status, new_frame_counter) = KYFG_GetGrabberValueInt(grabberHandle, "RXFrameCounter")
            if new_frame_counter <= frame_counter:
                error_count+=1
                print(f'\nERROR: on camera {camInfo.deviceModelName} while {i} iteration\nIncorrect acquisition:')
                print(f'frame_counter = {frame_counter}')
                print(f'new_frame_counter = {new_frame_counter}')
                break
            else: frame_counter = new_frame_counter
        (status, drop_frame_counter) = KYFG_GetGrabberValueInt(grabberHandle, "DropFrameCounter")
        (status,) = KYFG_CameraStop(cameraHandle)
        (status,) = KYFG_StreamDelete(streamHandle)
        (status,) = KYFG_SetGrabberValueEnum(grabberHandle, "TransferControlMode", 0)
        (status,) = KYFG_CameraClose(cameraHandle)
        if drop_frame_counter > 0:
            error_count += 1
            print(f'ERROR on camera {camInfo.deviceModelName}')
            print(f'drop_frame_counter = {drop_frame_counter}')
            continue
        print(f'Test for camera {camInfo.deviceModelName} is successful')
    (status,) = KYFG_Close(grabberHandle)
    print(f'error_count = {error_count}')
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
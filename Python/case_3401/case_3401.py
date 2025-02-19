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

class StreamCallbackStruct:
    def __init__(self):
        self.callbackCounter = 0
class EventCallbackStruct:
    def __init__(self):
        self.cameraHandle = 0

def streamCallbackFunction(buffHandle, userContext):
    if buffHandle == 0:
        return
    userContext.callbackCounter += 1
    try:
        (status,) = KYFG_BufferToQueue(buffHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
    except:
        return
    return
def eventCallbackFunction(userContext, event):
    if isinstance(event, KYDEVICE_EVENT_CAMERA_CONNECTION_LOST) == True:
        (status, camInfo) = KYFG_CameraInfo2(event.camHandle)
        print(camInfo.deviceModelName, 'connection lost event')
        (status,) = KYFG_CameraClose(event.camHandle)
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
    event_struct = EventCallbackStruct()
    (status,) = KYDeviceEventCallBackRegister(grabberHandle, eventCallbackFunction, py_object(event_struct))
    error_count = 0
    for i in range(len(camList)):
        cameraHandle = camList[i]
        (status,camInfo) = KYFG_CameraInfo2(cameraHandle)
        if "Iron" not in camInfo.deviceModelName:
            continue
        (status,) = KYFG_CameraOpen2(cameraHandle, None)
        print(camInfo.deviceModelName, 'is open')
        (status, streamHandle) = KYFG_StreamCreate(cameraHandle, 0)
        callback_struct = StreamCallbackStruct()
        (status,) = KYFG_StreamBufferCallbackRegister(streamHandle, streamCallbackFunction, callback_struct)
        number_of_buffers = [0 for i in range(16)]
        (status, payload_size, _, _) = KYFG_StreamGetInfo(streamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_PAYLOAD_SIZE)
        for iFrame in range(len(number_of_buffers)):
            (status, number_of_buffers[iFrame]) = KYFG_BufferAllocAndAnnounce(streamHandle, payload_size, 0)
        (status,) = KYFG_BufferQueueAll(streamHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_UNQUEUED,
                                        KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
        (status,) = KYFG_CameraStart(cameraHandle, streamHandle, 0)
        time.sleep(2)
        (status, frame_counter) = KYFG_GetGrabberValueInt(grabberHandle, "RXFrameCounter")
        (status, drop_frame_counter) = KYFG_GetGrabberValueInt(grabberHandle, "DropFrameCounter")
        if drop_frame_counter != 0 or frame_counter == 0:
            error_count += 1
        print("frame_counter", frame_counter)
        print("drop_frame_counter", drop_frame_counter)
        KYFG_CameraExecuteCommand(cameraHandle, "DeviceReset")
        time.sleep(3)
        print("DeviceReset")
        (status, frame_counter) = KYFG_GetGrabberValueInt(grabberHandle, "RXFrameCounter")
        (status, drop_frame_counter) = KYFG_GetGrabberValueInt(grabberHandle, "DropFrameCounter")
        print("frame_counter", frame_counter)
        print("drop_frame_counter", drop_frame_counter)
        if drop_frame_counter != 0 or frame_counter != 0:
            error_count += 1
        try:
            (status,) = KYFG_CameraOpen2(cameraHandle, None)
        except Exception as e:
            print(type(e), str(e))
        (status, camList) = KYFG_UpdateCameraList(grabberHandle)
        try:
            (status,) = KYFG_CameraOpen2(cameraHandle, None)
            time.sleep(1)
            (status,) = KYFG_CameraClose(cameraHandle)
        except Exception as e:
            print(type(e), str(e))
            error_count += 1
    (status,) = KYFG_Close(grabberHandle)
    assert error_count == 0, 'Test not passed'
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

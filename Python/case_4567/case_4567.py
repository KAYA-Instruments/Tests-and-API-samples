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


os.environ["WithAdapter"] = "1"


def streamCallbackFunction(buffHanle, userContext):
    if buffHanle == INVALID_STREAM_BUFFER_HANDLE or buffHanle ==NULL_STREAM_BUFFER_HANDLE:
        print("IncorrectBufferHandle", buffHanle)
    print(f"Good callback function received with buffer handle: 0x{str(buffHanle)}", end='\n')
    try:
        (status,) = KYFG_BufferToQueue(buffHanle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
    except:
        pass

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
    (status, timestamp) = KYFG_GetGrabberValueInt(grabberHandle, "Timestamp")
    KYFG_SetGrabberValueString(grabberHandle, "DeviceUserID", "20")
    print(f"Grabber Timestamp {timestamp}; status: {hex(status)}")
    print(f"Open grabber with Handle: {grabberHandle}")
    (status, cameraList) = KYFG_UpdateCameraList(grabberHandle)
    assert len(cameraList)> 0, "There are no cameras on this grabber"
    cameraHande = cameraList[0]
    (status, camInfo) = KYFG_CameraInfo2(cameraHande)
    (status,) = KYFG_CameraOpen2(cameraHande, None)
    print(f"Camera {camInfo.deviceModelName} is open")
    (status, pixelFormat) = KYFG_GetCameraValue(cameraHande, "PixelFormat")
    print(f"Camera pixel Format: {pixelFormat}")
    KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "PixelFormat", "RGB8")
    (status, streamHanlde) = KYFG_StreamCreate(cameraHande, 0)
    (status,) = KYFG_StreamBufferCallbackRegister(streamHanlde, streamCallbackFunction, None)
    number_of_buffer = 16
    buffers = [0 for i in range(number_of_buffer)]
    payloadSize = 0
    (status, payloadSize, _ ,_) = KYFG_StreamGetInfo(streamHanlde, KY_STREAM_INFO_CMD.KY_STREAM_INFO_PAYLOAD_SIZE)
    for IFrame in range(number_of_buffer):
        (status, buffers[IFrame]) = KYFG_BufferAllocAndAnnounce(streamHanlde, payloadSize, None)
    print("KY_STREAM_INFO_PAYLOAD_SIZE:", payloadSize)

    (status,) = KYFG_BufferQueueAll(streamHanlde, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_UNQUEUED, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
    (status,) = KYFG_CameraStart(cameraHande, streamHanlde, 0)
    time.sleep(3)
    (status,) = KYFG_CameraStop(cameraHande)
    (status,) = KYFG_StreamBufferCallbackUnregister(streamHanlde, streamCallbackFunction)
    (status,) = KYFG_StreamDelete(streamHanlde)
    (status,) = KYFG_CameraClose(cameraHande)
    (status,) = KYFG_Close(grabberHandle)

    print(f'\nExiting from CaseRun({args}) with code SUCCESS...')
    return CaseReturnCode.SUCCESS


# The flow starts here
if __name__ == "__main__":
    # try:
        args_ = ParseArgs()
        return_code = CaseRun(args_)
        print(f'Case return code: {return_code}')
    # except Exception as ex:
    #     print(f"Exception of type {type(ex)} occurred: {str(ex)}")
    #     exit(-200)
    #
    # exit(return_code)

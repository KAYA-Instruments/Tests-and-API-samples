# Common KAYA imports DO NOT EDIT!!!
import sys
import os
import argparse
import time

sys.path.insert(0, os.environ['KAYA_VISION_POINT_PYTHON_PATH'])
from KYFGLib import *

# Common Case imports DO NOT EDIT!!!
from enum import IntEnum  # for CaseReturnCode

# additional imports required by particular case, ADD CASE SPECIFIC IMPORTS UNDER THIS LINE:

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

class StreamStruct:
    def __init__(self):
        self.callbackCounter = 0
        self.streamHandle = 0
        self.cameraHandle = 0
        self.isAcquisition = False

def streamCallbackFunction(buffer, userContext):
    if buffer == INVALID_STREAM_BUFFER_HANDLE:
        return
    if userContext.callbackCounter == 30:
        userContext.isAcquisition = False
        KYFG_CameraStop(userContext.cameraHandle)
        KYFG_CameraStop(userContext.cameraHandle)

    try:
        KYFG_BufferToQueue(buffer, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
    except:
        pass
    userContext.callbackCounter += 1

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
    assert len(cameraList) > 0, 'There is no cameras on this grabber'
    cameraHandle = cameraList[0]
    (status, camInfo) = KYFG_CameraInfo2(cameraHandle)
    print(f"Camera {camInfo.deviceModelName} is opened for test")
    (status,) = KYFG_CameraOpen2(cameraHandle, None)
    (status, streamHandle) = KYFG_StreamCreate(cameraHandle, 0)
    streamStruct = StreamStruct()
    streamStruct.cameraHandle = cameraHandle
    streamStruct.streamHandle = streamHandle

    KYFG_StreamBufferCallbackRegister(streamHandle, streamCallbackFunction, streamStruct)
    number_of_buffers = 16
    buffers = [0 for i in range(number_of_buffers)]
    (status, paloadSize, _, _) = KYFG_StreamGetInfo(streamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_PAYLOAD_SIZE)
    for IFrame in range(len(buffers)):
        (status, buffers[IFrame]) = KYFG_BufferAllocAndAnnounce(streamHandle, paloadSize, None)
    (status,) = KYFG_BufferQueueAll(streamHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_UNQUEUED, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
    (status,) = KYFG_CameraStart(cameraHandle, streamHandle, 0)
    streamStruct.isAcquisition = True
    i = 0
    while True:
        time.sleep(1)
        i += 1
        if not streamStruct.isAcquisition:
            break
        if i > 10:
            assert streamStruct.callbackCounter > 0, "acquisition not started"
    KYFG_StreamBufferCallbackUnregister(streamHandle, streamCallbackFunction)
    KYFG_StreamDelete(streamHandle)
    KYFG_CameraClose(cameraHandle)
    (status,) = KYFG_Close(grabberHandle)
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

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
    parser.add_argument('--streamDuration', type=int, default=5, help='Stream duration for each camera in seconds')
    return parser

def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)
############
# Classes
############
class StreamCallbackStruct:
    def __init__(self):
        self.callbackCounter = 0
############
# Functions
############
def streamCallbackFunc(buffHandle, userContext):
    if buffHandle == NULL_STREAM_BUFFER_HANDLE or buffHandle == INVALID_STREAM_BUFFER_HANDLE:
        return
    # print('Good callback streams buffer handle: ' + str(format(int(buffHandle), '02x')), end='\r')
    userContext.callbackCounter += 1
    # sys.stdout.flush()
    try:
        (KYFG_BufferToQueue_status,) = KYFG_BufferToQueue(buffHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
    except:
        return
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
    streamDuration = args['streamDuration']
    error_count = 0
    (grabberHandle,) = KYFG_Open(device_index)
    (status, cameraList) = KYFG_UpdateCameraList(grabberHandle)
    assert len(cameraList) > 0, "There are no cameras on this grabber"
    if len(cameraList) == 1:
        print('Need more than 1 camera for this test')
        return CaseReturnCode.NO_HW_FOUND
    streamHandleList = []
    callbackStructList = []
    # Open all of cameras
    for cameraHandle in cameraList:
        (status, camInfo) = KYFG_CameraInfo2(cameraHandle)
        (status,) = KYFG_CameraOpen2(cameraHandle, None)
        print(f"Camera {camInfo.deviceModelName} is open")
        try:
            if KYFG_IsGrabberValueImplemented(grabberHandle, 'TriggerMode'):
                KYFG_SetGrabberValueEnum(grabberHandle, "TriggerMode", 0)
            if KYFG_IsCameraValueImplemented(cameraHandle, "TriggerMode"):
                KYFG_SetCameraValueEnum(cameraHandle, "TriggerMode", 0)
            if KYFG_IsCameraValueImplemented(cameraHandle, "SimulationTriggerMode"):
                KYFG_SetCameraValueEnum(cameraHandle, "SimulationTriggerMode", 0)
        except:
            pass
    for cameraHandle in cameraList:
        (status, camInfo) = KYFG_CameraInfo2(cameraHandle)
        (status, streamHandle) = KYFG_StreamCreate(cameraHandle, 0)
        streamHandleList.append(streamHandle)
        streamCallbackStruct = StreamCallbackStruct()
        callbackStructList.append(streamCallbackStruct)
        print(f'CameraHandle: {hex(cameraHandle)}; streamHandle: {streamHandle}')
        (status,) = KYFG_StreamBufferCallbackRegister(streamHandle, streamCallbackFunc, streamCallbackStruct)
        (_, payload_size, _, _) = KYFG_StreamGetInfo(streamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_PAYLOAD_SIZE)
        (_, buf_allignment, _, _) = KYFG_StreamGetInfo(streamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_BUF_ALIGNMENT)
        streamBufferHandle = [0 for i in range(16)]
        streamAllignedBuffer = [0 for i in range(16)]
        for iFrame in range(len(streamBufferHandle)):
            streamAllignedBuffer[iFrame] = aligned_array(buf_allignment, c_ubyte, payload_size)
            (status, streamBufferHandle[iFrame]) = KYFG_BufferAnnounce(streamHandle, streamAllignedBuffer[iFrame], None)
        (status,) = KYFG_BufferQueueAll(streamHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_UNQUEUED,
                                        KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
        print(f'CameraHandle: {hex(cameraHandle)}; streamHandle: {streamHandle}')
        (status,) = KYFG_CameraStart(cameraHandle, streamHandle, 0)
        print(f"Camera {camInfo.deviceModelName} stream started")
    time.sleep(streamDuration)
    print(cameraList)
    print(streamHandleList)
    print(callbackStructList)
    for cameraHandle in cameraList:
        print('cameraHandle', cameraHandle)
        streamHandle = streamHandleList[cameraList.index(cameraHandle)]
        streamCallbackStruct = callbackStructList[cameraList.index(cameraHandle)]
        (status, camInfo) = KYFG_CameraInfo2(cameraHandle)
        (status,) = KYFG_CameraStop(cameraHandle)
        KYFG_SetGrabberValueInt(grabberHandle, "CameraSelector", cameraList.index(cameraHandle))
        (status, frame_counter) = KYFG_GetGrabberValueInt(grabberHandle, "RXFrameCounter")
        (status, drop_frame_counter) = KYFG_GetGrabberValueInt(grabberHandle, "DropFrameCounter")
        (status,) = KYFG_StreamBufferCallbackUnregister(streamHandle, streamCallbackFunc)
        (status,) = KYFG_StreamDelete(streamHandle)
        (status,) = KYFG_CameraClose(cameraHandle)
        print(f"Camera {camInfo.deviceModelName} Closed")
        print("frame_counter: ", frame_counter)
        print("drop_frame_counter: ", drop_frame_counter)
        print("callbackCounter: ", streamCallbackStruct.callbackCounter)
        if drop_frame_counter > 0 or frame_counter == 0 or streamCallbackStruct.callbackCounter == 0:
            print("Camera test not Passed")
            error_count +=1
    assert error_count == 0, "Test not Passed"
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

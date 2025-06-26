# Common KAYA imports DO NOT EDIT!!!
import sys
import os
import argparse
sys.path.insert(0, os.environ['KAYA_VISION_POINT_PYTHON_PATH'])
#os.environ["WithAdapter"] = "1" # uncomment this section to work through Vision Point II Adapter
from KYFGLib import *

# Common Case imports DO NOT EDIT!!!
from enum import IntEnum  # for CaseReturnCode

# additional imports required by particular case, ADD CASE SPECIFIC IMPORTS UNDER THIS LINE:
# For example:
# import numpy as np
# import cv2
# from numpngw import write_png
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
    parser.add_argument('--ExpectedFPS', default=10, type=int, help='ExpectedFPS')
    parser.add_argument('--streamDuration', default=10, type=int, help='streamDuration')
    return parser


def Reset_Grabber(grabberHandle):
    pass
    # Grabber initialization for this specific test


def Reset_camera(cameraHandle):
    pass
    # Camera initialization for this specific test



def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)


##########
# Classes
##########
class StreamCallbackStruct():
    def __init__(self):
        self.callbackCounter = 0
        self.firstTimestamp = 0
        self.timestamps = []


##########
# Functions
##########
def streamCallbackFunc(buffHandle, userContext):
    if buffHandle == 0:
        print("BUFF Handle = 0")
        return
    # print('Frame')
    streamInfo = cast(userContext, py_object).value
    # print('Good callback streams buffer handle: ' + str(format(int(buffHandle), '02x')), end='\r')
    # userContext.callbackCounter += 1

    (KYFG_BufferGetInfo_status, pInfoTimestamp, pInfoSize, pInfoType) = KYFG_BufferGetInfo(
        buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_TIMESTAMP)  # UINT64
    if streamInfo.callbackCounter == 0:
        streamInfo.firstTimestamp = pInfoTimestamp
    streamInfo.timestamps.append(pInfoTimestamp-streamInfo.firstTimestamp)
    streamInfo.callbackCounter += 1
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

    # Other parameters used by this particular case
    ExpectedFPS = args['ExpectedFPS']
    streamDuration = args['streamDuration']
    (grabberHandle,) = KYFG_Open(device_index)
    (status, cameraList) = KYFG_UpdateCameraList(grabberHandle)
    if len(cameraList) < 2:
        print(len(cameraList), 'cameras detected')
        return CaseReturnCode.NO_HW_FOUND
    # Grabber trigger setting
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, 'TimerSelector', "Timer0")
    FrameTime = 1e+6 / ExpectedFPS
    (status,) = KYFG_SetGrabberValueFloat(int(grabberHandle), 'TimerDelay', FrameTime / 2)
    (status,) = KYFG_SetGrabberValueFloat(int(grabberHandle), 'TimerDuration', FrameTime / 2)
    (status,) = KYFG_SetGrabberValueEnum(grabberHandle, "TimerTriggerSource", 0)
    streamHandle_array = []
    streamStructsArray = []
    for cameraHandle in cameraList:
        (status,) = KYFG_CameraOpen2(cameraHandle, None)
        if not KYFG_IsCameraValueImplemented(cameraHandle, "TriggerMode") and not KYFG_IsCameraValueImplemented(cameraHandle, "SimulationTriggerMode"):
            return CaseReturnCode.NO_HW_FOUND
        (status, camInfo) = KYFG_CameraInfo2(cameraHandle)
        print(f'\n*** Camera {camInfo.deviceModelName} opened ***')
        (status,) = KYFG_SetGrabberValueInt(int(grabberHandle), 'CameraSelector', cameraList.index(cameraHandle))
        (status,) = KYFG_SetGrabberValueEnum(grabberHandle, "CameraTriggerMode", 1)
        (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, 'CameraTriggerActivation', "AnyEdge")
        (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, 'CameraTriggerSource', "KY_TIMER_ACTIVE_0")
        KYFG_SetCameraValueEnum(cameraHandle, "TriggerMode", 1)
        KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "TriggerSource", 'LinkTrigger0')
        KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "ExposureAuto", "Off")
        KYFG_SetCameraValueFloat(cameraHandle, "ExposureTime", 5000.0)
        # stream preparation
        (status, streamHandle) = KYFG_StreamCreate(cameraHandle, 0)
        streamHandle_array.append(streamHandle)
        streamCallbackStruct = StreamCallbackStruct()
        streamStructsArray.append(streamCallbackStruct)
        (status,) = KYFG_StreamBufferCallbackRegister(streamHandle, streamCallbackFunc,
                                                      py_object(streamCallbackStruct))
        (_, payload_size, _, _) = KYFG_StreamGetInfo(streamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_PAYLOAD_SIZE)
        (_, buf_allignment, _, _) = KYFG_StreamGetInfo(streamHandle,
                                                       KY_STREAM_INFO_CMD.KY_STREAM_INFO_BUF_ALIGNMENT)
        streamBufferHandle = [0 for i in range(100)]
        # streamAllignedBuffer = [0 for i in range(32)]
        for iFrame in range(len(streamBufferHandle)):
            # streamAllignedBuffer[iFrame] = aligned_array(buf_allignment, c_ubyte, payload_size)
            # (status, streamBufferHandle[iFrame]) = KYFG_BufferAnnounce(streamHandle, streamAllignedBuffer[iFrame], None)
            (status, streamBufferHandle[iFrame]) = KYFG_BufferAllocAndAnnounce(streamHandle, payload_size, None)

        (status,) = KYFG_BufferQueueAll(streamHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_UNQUEUED,
                                        KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
        print(f'GrabberHandle: {grabberHandle} \nCameraHandle: {hex(cameraHandle)} \nStreamHandle: {streamHandle}')
        print('Stream preparation completed')
        (status,) = KYFG_CameraStart(cameraHandle, streamHandle, 0)
        print(f"Camera {camInfo.deviceModelName} stream started")
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, 'TimerSelector', "Timer0")
    (status,) = KYFG_SetGrabberValueEnum(grabberHandle, "TimerTriggerSource", 42)  # Continuous
    time.sleep(streamDuration)
    (status,) = KYFG_SetGrabberValueEnum(grabberHandle, "TimerTriggerSource", 0)
    is_test_passed = True
    for cameraHandle in cameraList:
        print(f"\n*** Stats for CameraHandle {cameraHandle} ***")
        streamHandle = streamHandle_array[cameraList.index(cameraHandle)]
        streamCallbackStruct = streamStructsArray[cameraList.index(cameraHandle)]
        (status, camInfo) = KYFG_CameraInfo2(cameraHandle)
        (status,) = KYFG_CameraStop(cameraHandle)
        (status,) = KYFG_StreamBufferCallbackUnregister(streamHandle, streamCallbackFunc)
        (status,) = KYFG_SetGrabberValueInt(int(grabberHandle), "CameraSelector", cameraList.index(cameraHandle))
        (status, frame_counter) = KYFG_GetGrabberValueInt(grabberHandle, "RXFrameCounter")
        (status, drop_frame_counter) = KYFG_GetGrabberValueInt(grabberHandle, "DropFrameCounter")
        (status,) = KYFG_StreamDelete(streamHandle)
        KYFG_SetCameraValueEnum(cameraHandle, "TriggerMode", 0)
        KYFG_SetGrabberValueEnum(grabberHandle, "CameraTriggerMode", 0)
        (status,) = KYFG_CameraClose(cameraHandle)
        print(f"{camInfo.deviceModelName} successfully closed")
        print("RXFrameCounter:   ", frame_counter)
        print("DropFrameCounter: ", drop_frame_counter)
        print("CallbackCounter:  ", streamCallbackStruct.callbackCounter)
        if frame_counter == 0 or drop_frame_counter > 0:
            is_test_passed = False
    differences = []
    for i in range(len(streamStructsArray[0].timestamps)):
        difference = streamStructsArray[0].timestamps[i] - streamStructsArray[1].timestamps[i]
        differences.append(difference)
        print(f"{i + 1}: ", streamStructsArray[0].timestamps[i], (streamStructsArray[1].timestamps[i]),
              difference)
    
    (status,) = KYFG_Close(int(grabberHandle))
    assert is_test_passed, 'Test not passed: frame_counter == 0 or drop_frame_counter > 0'
    assert abs(sum(differences)/len(differences)) < 1e+4, 'Test not passed: Difference between timestamps to large'

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

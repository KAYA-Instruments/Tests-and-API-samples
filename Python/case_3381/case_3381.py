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
import numpy as np


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
    parser.add_argument('--duration', type=int, default=3, help='Stream duration in seconds')
    return parser


def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)


##########
# Classes
##########
class StreamStruct:
    def __init__(self):
        self.firstFrame = []
        self.currentFrame = []
        self.callbackCounter = 0
        self.errorCount = 0
        return


##########
# Functions
##########
def numpy_from_data(buffData, buffSize, datatype):
    data_pointer = ctypes.cast(buffData, ctypes.c_char_p)
    buffer_from_memory = ctypes.pythonapi.PyMemoryView_FromMemory
    buffer_from_memory.restype = ctypes.py_object
    # buffer_from_memory.restype=ctypes.c_uint16
    buffer = buffer_from_memory(data_pointer, buffSize)
    return np.frombuffer(buffer, datatype)


def streamCallbackFunction(buffHandle, userContext):
    if buffHandle == NULL_STREAM_BUFFER_HANDLE or buffHandle == INVALID_STREAM_BUFFER_HANDLE:
        return
    (KYFG_BufferGetInfo_status, pInfoBase, pInfoSize, pInfoType) = KYFG_BufferGetInfo(
        buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_BASE)  # PTR
    (KYFG_BufferGetInfo_status, pInfoSize, pInfo, pInfoType) = KYFG_BufferGetInfo(
        buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_SIZE)  # SIZET
    buff_data = numpy_from_data(pInfoBase, pInfoSize, c_uint16)
    if userContext.callbackCounter == 0:
        userContext.firstFrame = buff_data.copy()
    else:
        userContext.currentFrame = buff_data.copy()
        if not np.array_equal(userContext.firstFrame, userContext.currentFrame):
            print(f'Error while comparison {userContext.callbackCounter + 1} frame')
            userContext.errorCount += 1

    userContext.callbackCounter += 1
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
    duration = args['duration']
    (status, device_info) = KY_DeviceInfo(device_index)
    if device_info.m_Protocol != KY_DEVICE_PROTOCOL.KY_DEVICE_PROTOCOL_CoaXPress:
        print('Test could not run on this grabber')
        return CaseReturnCode.COULD_NOT_RUN
    (grabberHandle,) = KYFG_Open(device_index)
    (status, cameraList) = KYFG_UpdateCameraList(grabberHandle)
    assert len(cameraList) != 0, 'There are no cameras on this grabber'
    cameraHandle = None
    for cam in cameraList:
        (status, camInfo) = KYFG_CameraInfo2(cam)
        if "Chameleon" in camInfo.deviceModelName:
            cameraHandle = cam
    if cameraHandle is None:
        print('There is no Chameleon on this grabber')
        return CaseReturnCode.NO_HW_FOUND
    (status,) = KYFG_CameraOpen2(cameraHandle, None)
    # grabber parameters setting
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "TimerSelector", "Timer0")
    (status,) = KYFG_SetGrabberValueFloat(grabberHandle, "TimerDelay", 246.304)
    (status,) = KYFG_SetGrabberValueFloat(grabberHandle, "TimerDuration", 246.304)
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "TimerActivation", "RisingEdge")
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "TimerTriggerSource", "KY_CONTINUOUS")
    # extended stream features
    (status,) = KYFG_SetGrabberValueInt(grabberHandle, "CameraSelector", 0)
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "CameraTriggerMode", "On")
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "CameraTriggerActivation", "AnyEdge")
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "CameraTriggerSource", "KY_TIMER_ACTIVE_0")
    # camera parameters setting
    (status,) = KYFG_SetCameraValueInt(cameraHandle, "Width", 4608)
    (status,) = KYFG_SetCameraValueInt(cameraHandle, "Height", 100)
    (status,) = KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "PixelFormat", "Mono10")
    (status,) = KYFG_SetCameraValueFloat(cameraHandle, "AcquisitionFrameRate", 1e+6)
    (status,) = KYFG_SetCameraValueBool(cameraHandle, "VideoSourceMovingFrames", False)
    (status,) = KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "ConnectionConfig", "x2_CXP_6")
    (status,) = KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "ConnectionConfigDefault", "x2_CXP_6")
    (status,) = KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "SimulationTriggerMode", "Triggered")
    (status,) = KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "SimulationTriggerActivation", "RisingEdge")
    (status,) = KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "SimulationTriggerSource", "KY_CAM_TRIG")
    streamStruct = StreamStruct()
    (status, streamHandle) = KYFG_StreamCreate(cameraHandle, 0)
    (status,) = KYFG_StreamBufferCallbackRegister(streamHandle, streamCallbackFunction, streamStruct)
    streamBufferHandle = [0 for i in range(16)]
    (status, payload_size, frameDataSize, pInfoType) = KYFG_StreamGetInfo(streamHandle,
                                                                          KY_STREAM_INFO_CMD.KY_STREAM_INFO_PAYLOAD_SIZE)
    for i in range(len(streamBufferHandle)):
        (status, streamBufferHandle[i]) = KYFG_BufferAllocAndAnnounce(streamHandle, payload_size, None)
    (status,) = KYFG_BufferQueueAll(streamHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_UNQUEUED,
                                    KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
    last_frame_count = 0
    (status,) = KYFG_CameraStart(cameraHandle, streamHandle, 0)
    correctly_acquisition = True
    for i in range(duration):
        time.sleep(1)
        if last_frame_count == 0:
            (status, last_frame_count) = KYFG_GetGrabberValueInt(grabberHandle, "RXFrameCounter")
            continue
        (status, frame_counter) = KYFG_GetGrabberValueInt(grabberHandle, "RXFrameCounter")
        if last_frame_count == frame_counter:
            print('Acquisition unexpectedly stopped')
            correctly_acquisition = False
            break
        else:
            last_frame_count = frame_counter

    (status,) = KYFG_CameraStop(cameraHandle)

    (status,) = KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "SimulationTriggerMode", "FreeRun")
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "CameraTriggerMode", "Off")
    (status,) = KYFG_StreamBufferCallbackUnregister(streamHandle, streamCallbackFunction)
    (status,) = KYFG_StreamDelete(streamHandle)
    (status,) = KYFG_CameraClose(cameraHandle)
    (status,) = KYFG_Close(grabberHandle)
    print('frame_counter = ', last_frame_count)
    print('CallbackCounter = ', streamStruct.callbackCounter)
    print('ErrorCounter = ', streamStruct.errorCount)
    assert streamStruct.errorCount == 0 and correctly_acquisition, "Test not passed"
    assert last_frame_count != 0 and streamStruct.callbackCounter != 0, "Test not passed"
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

# Common KAYA imports DO NOT EDIT!!!
import sys
import os
import argparse
sys.path.insert(0, os.environ['KAYA_VISION_POINT_PYTHON_PATH'])
from KYFGLib import *

# Common Case imports DO NOT EDIT!!!
from enum import IntEnum  # for CaseReturnCode

# additional imports required by particular case, ADD CASE SPECIFIC IMPORTS UNDER THIS LINE:
import numpy as np
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
    parser.add_argument('--pixelFormat', type=str, default="RGB8", help='pixel format')
    parser.add_argument('--cameraModel', type=str, default="Chameleon", help='cameraModel')
    return parser

def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)

def numpy_from_data(buffData, buffSize, datatype):
    data_pointer = ctypes.cast(buffData, ctypes.c_char_p)
    buffer_from_memory = ctypes.pythonapi.PyMemoryView_FromMemory
    buffer_from_memory.restype = ctypes.py_object
    buffer = buffer_from_memory(data_pointer, buffSize)
    return np.frombuffer(buffer, datatype)

class CallbackStruct:
    def __init__(self):
        self.width=0
        self.height=0
        self.data=[]
        self.datatype=np.uint8
        self.callbackCounter=0
        self.bitness=8
        self.callbackErrorCounter=0
        self.upper_threshold=0

def callbackFunc(buffHandle, userContext):
    if (buffHandle == 0):
        return
    print('Good callback streams buffer handle: ' + str(buffHandle))
    (KYFG_BufferToQueue_status,) = KYFG_BufferToQueue(buffHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
    (_, buffData, _, _) = KYFG_BufferGetInfo(buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_BASE)
    (_, buffSize, _, _) = KYFG_BufferGetInfo(buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_SIZE)

    userContext.callbackCounter += 1
    userContext.data = numpy_from_data(buffData, buffSize, userContext.datatype)
    userContext.upper_threshold=pow(2,userContext.bitness)-1

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
    pixelFormat = args['pixelFormat']
    cameraModel = args['cameraModel']

    (grabberHandle,) = KYFG_Open(device_index)
    (status,cameraList) = KYFG_UpdateCameraList(grabberHandle)
    if len(cameraList) == 0:
        print(f"No cameras found on this system by model name '{cameraModel}'.")
        return CaseReturnCode.NO_HW_FOUND
    camHandle = 0
    for cameraHandle in cameraList:
        (status, camInfo) = KYFG_CameraInfo2(cameraHandle)
        if cameraModel in camInfo.deviceModelName:
            camHandle = cameraHandle
            break
    if camHandle == 0:
        print(f'There is no camera {cameraModel} on this grabber')
        return CaseReturnCode.NO_HW_FOUND
    (status,) = KYFG_CameraOpen2(camHandle, None)
    # check trigger mode
    try:
        if KYFG_IsGrabberValueImplemented(grabberHandle, 'TriggerMode'):
            KYFG_SetGrabberValueEnum(grabberHandle, "TriggerMode", 0)
        if KYFG_IsCameraValueImplemented(camHandle, "TriggerMode"):
            KYFG_SetCameraValueEnum(camHandle, "TriggerMode", 0)
        if KYFG_IsCameraValueImplemented(camHandle, "SimulationTriggerMode"):
            KYFG_SetCameraValueEnum(camHandle, "SimulationTriggerMode", 0)
    except:
        pass
    (status, camInfo) = KYFG_CameraInfo2(camHandle)
    print(f'Camera {camInfo.deviceModelName} is open' )
    (status,) = KYFG_SetCameraValueEnum_ByValueName(camHandle, 'PixelFormat', pixelFormat)
    print(f'Pixel Format: {pixelFormat}')
    (status, width) = KYFG_GetCameraValueInt(camHandle, "Width")
    (status, height) = KYFG_GetCameraValueInt(camHandle, "Height")
    callbackStruct=CallbackStruct()
    callbackStruct.width=width
    callbackStruct.height=height
    if pixelFormat.endswith('8'):
        callbackStruct.datatype=c_uint8
        callbackStruct.bitness=8
    else:
        callbackStruct.datatype = c_uint16
        callbackStruct.bitness=int(pixelFormat[-2:])
    print(f'Bitness: {callbackStruct.bitness}')
    (status, cameraStreamHandle) = KYFG_StreamCreate(camHandle, 0)
    (KYFG_StreamBufferCallbackRegister_status,) = KYFG_StreamBufferCallbackRegister(cameraStreamHandle,
                                                                                    callbackFunc,
                                                                                    callbackStruct)
    # Retrieve information about required frame buffer size and alignment
    (KYFG_StreamGetInfo_status, payload_size, frameDataSize, pInfoType) = \
        KYFG_StreamGetInfo(cameraStreamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_PAYLOAD_SIZE)

    (KYFG_StreamGetInfo_status, buf_allignment, frameDataAlignment, pInfoType) = \
        KYFG_StreamGetInfo(cameraStreamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_BUF_ALIGNMENT)
    # allocate memory for desired number of frame buffers
    number_of_buffers = 1
    streamAlignedBuffer={}
    streamBufferHandle = {}
    for iFrame in range(number_of_buffers):
        streamAlignedBuffer[iFrame] = aligned_array(buf_allignment, c_ubyte, payload_size)
        (status, streamBufferHandle[iFrame]) = KYFG_BufferAnnounce(cameraStreamHandle,
                                                                   streamAlignedBuffer[iFrame], None)
    (KYFG_BufferQueueAll_status,) = KYFG_BufferQueueAll(cameraStreamHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_UNQUEUED,
                                                        KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
    (KYFG_CameraStart_status,) = KYFG_CameraStart(camHandle, cameraStreamHandle, 1)
    time.sleep(1)
    (status,) = KYFG_CameraStop(camHandle)
    (status,) = KYFG_StreamBufferCallbackUnregister(cameraStreamHandle,callbackFunc)
    print(callbackStruct.upper_threshold)
    if all(0 <= x <= callbackStruct.upper_threshold for x in callbackStruct.data):
        print('Same bitness')
    else:
        print('Different bitness')
        callbackStruct.callbackErrorCounter += 1
    (status,) = KYFG_StreamDelete(cameraStreamHandle)
    (status,) = KYFG_CameraClose(camHandle)
    (status,) = KYFG_Close(grabberHandle)
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
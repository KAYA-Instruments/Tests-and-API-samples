# Common KAYA imports DO NOT EDIT!!!
import sys
import os
import argparse
sys.path.insert(0, os.environ['KAYA_VISION_POINT_PYTHON_PATH'])
from KYFGLib import *

# Common Case imports DO NOT EDIT!!!
from enum import IntEnum  # for CaseReturnCode

# additional imports required by particular case, ADD CASE SPECIFIC IMPORTS UNDER THIS LINE:
import struct
import math
import time
import pathlib
import numpy as np
from PIL import Image


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
    parser.add_argument('--numberOfFrames', type=int,default=1000)
    parser.add_argument('--imageName', type=str, default='Horizontal.png', help='Name of image')
    parser.add_argument('--pixelFormat', type=str,default="RGB16", help='Pixel format for image')
    return parser

def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)

class StreamInfoStruct:
    def __init__(self):
        self.height = 0
        self.width = 0
        self.frameData = []
        self.imageData = []
        self.callbackCount = 0
        self.error_count = 0
        self.chanels = 0
        self.framesArray = []
        self.dtype=np.uint8
        return

def streamCallbackFunc(buffHandle, userContext):
    if (buffHandle == 0 ):
        return
    userContext.callbackCount += 1
    (KYFG_BufferGetInfo_status, buffData, pInfoSize, pInfoType) = KYFG_BufferGetInfo(
        buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_BASE)
    (KYFG_BufferGetInfo_status, buffSize, pInfoSize, pInfoType) = KYFG_BufferGetInfo(
        buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_SIZE)
    frameData = numpy_from_data(buffData, buffSize, userContext.dtype)
    frameData = frameData.reshape(userContext.height, userContext.width, userContext.chanels)
    userContext.framesArray.append(frameData)
    if (frameData == userContext.imageData).all():
        print(f'{userContext.callbackCount} FRAME ARE EQUALS')
    else:
        print(f'{userContext.callbackCount} frame are not equals')
        userContext.error_count += 1
    try:
        (KYFG_BufferToQueue_status,) = KYFG_BufferToQueue(buffHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
    except:return
    return

def numpy_from_data(buffData, buffSize, datatype):
    data_pointer= ctypes.cast(buffData, ctypes.c_char_p)
    buffer_from_memory = ctypes.pythonapi.PyMemoryView_FromMemory
    buffer_from_memory.restype = ctypes.py_object
    # buffer_from_memory.restype=ctypes.c_uint16
    buffer = buffer_from_memory(data_pointer, buffSize)
    return np.frombuffer(buffer, datatype)
def get_tranformation_factor(pixel_format: str):
    bintess = 8 if pixel_format.endswith('8') else int(pixel_format[-2:])
    return bintess-8
def waitForSleep(sleepTime):
    threadSleepSeconds = sleepTime
    print(f"Thread sleep for {threadSleepSeconds} seconds: ")
    for remaining in range(threadSleepSeconds, 0, -1):
        sys.stdout.write("\r")
        sys.stdout.write("{:2d} seconds remaining".format(remaining))
        sys.stdout.flush()
        time.sleep(1)
    sys.stdout.write("\rComplete!            \n")
    return threadSleepSeconds


def get_dtype(pixelFormat: str):
    return np.uint8 if pixelFormat.endswith('8') else np.uint16


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
    (status, device_info) = KY_DeviceInfo(device_index)
    if device_info.m_Protocol != KY_DEVICE_PROTOCOL.KY_DEVICE_PROTOCOL_CoaXPress:
        print('Test could not run on this grabber')
        return CaseReturnCode.COULD_NOT_RUN
    numberOfFrames=args['numberOfFrames']
    imagePath=str(pathlib.Path(__file__).parent.joinpath(args['imageName']).absolute())
    image = Image.open(imagePath)
    pixelFormat = args['pixelFormat']
    streamStruct = StreamInfoStruct()
    streamStruct.dtype = get_dtype(pixelFormat)
    transformation_factor = get_tranformation_factor(pixelFormat)
    image_matrix = (np.array(image, dtype=streamStruct.dtype))*pow(2,transformation_factor)
    (grabberHandle,) = KYFG_Open(device_index)
    (status, camerasList) = KYFG_UpdateCameraList(grabberHandle)
    cameraHandle = 0
    for camHandle in camerasList:
        (status, cameraInfo) = KYFG_CameraInfo2(camHandle)
        if 'Chameleon' in cameraInfo.deviceModelName:
            cameraHandle = camHandle
            break
    if cameraHandle == 0:
        print('There is no Chameleon on this grabber')
        return CaseReturnCode.NO_HW_FOUND
    (status, cameraInfo) = KYFG_CameraInfo2(cameraHandle)
    (status,) = KYFG_CameraOpen2(cameraHandle, None)
    try:
        if KYFG_IsGrabberValueImplemented(grabberHandle, 'TriggerMode'):
            KYFG_SetGrabberValueEnum(grabberHandle, "TriggerMode", 0)
        if KYFG_IsCameraValueImplemented(cameraHandle, "TriggerMode"):
            KYFG_SetCameraValueEnum(cameraHandle, "TriggerMode", 0)
    except:
        pass
    (status, fps) = KYFG_GetCameraValueFloat(cameraHandle, "AcquisitionFrameRate")
    duration = math.ceil(numberOfFrames/fps)
    (status,) = KYFG_SetCameraValueInt(cameraHandle, "Width", int(image.width))
    (status,) = KYFG_SetCameraValueInt(cameraHandle, "Height", int(image.height))
    (status,) = KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "PixelFormat", pixelFormat)
    (status,) = KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "VideoSourceType", "File")
    (status,) = KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "VideoSourceFileType", "Png")
    (status,) = KYFG_SetCameraValueString(cameraHandle, "SourceFilePath", imagePath)
    (status, pathValue) = KYFG_GetCameraValueStringCopy(cameraHandle, "SourceFilePath")
    assert pathValue == imagePath, 'Error while setting file path'

    streamStruct.imageData = image_matrix
    streamStruct.height = int(image.height)
    streamStruct.width = int(image.width)
    streamStruct.chanels = 3
    number_of_buffers = 16
    streamBufferHandle = {}
    streamAlignedBuffer = {}
    (status, streamHandle) = KYFG_StreamCreate(cameraHandle, 0)
    (status,) = KYFG_StreamBufferCallbackRegister(streamHandle, streamCallbackFunc, streamStruct)
    # Retrieve information about required frame buffer size and alignment
    (KYFG_StreamGetInfo_status, payload_size, frameDataSize, pInfoType) = \
        KYFG_StreamGetInfo(streamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_PAYLOAD_SIZE)

    (KYFG_StreamGetInfo_status, buf_allignment, frameDataAlignment, pInfoType) = \
        KYFG_StreamGetInfo(streamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_BUF_ALIGNMENT)

    # allocate memory for desired number of frame buffers
    for iFrame in range(number_of_buffers):
        streamAlignedBuffer[iFrame] = aligned_array(buf_allignment, c_ubyte, payload_size)
        # print("Address of alligned array: " + hex(addressof(streamAllignedBuffer[iFrame])))
        (status, streamBufferHandle[iFrame]) = KYFG_BufferAnnounce(streamHandle,
                                                                   streamAlignedBuffer[iFrame], None)
    (status,) = KYFG_BufferQueueAll(streamHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_UNQUEUED,
                                                        KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
    (status,) = KYFG_CameraStart(cameraHandle, streamHandle, numberOfFrames)
    waitForSleep(duration)
    assert streamStruct.callbackCount != 0, "Acquisition is not started"
    while streamStruct.callbackCount < numberOfFrames:
        waitForSleep(1)
    (status,) = KYFG_CameraStop(cameraHandle)
    nparray=streamStruct.framesArray
    (status,) = KYFG_StreamBufferCallbackUnregister(streamHandle, streamCallbackFunc)
    (status,) = KYFG_StreamDelete(streamHandle)
    (status,) = KYFG_CameraClose(cameraHandle)
    (status,) = KYFG_Close(grabberHandle)
    assert streamStruct.error_count == 0, 'Test not passed'
    print(f'\nExiting from CoreRun({args}) with code 0...')
    return CaseReturnCode.SUCCESS


if __name__ == "__main__":
    try:
        args_ = ParseArgs()
        return_code = CaseRun(args_)
        print(f'Case return code: {return_code}')
    except Exception as ex:
        print(f"Exception of type {type(ex)} occurred: {str(ex)}")
        exit(-200)

    exit(return_code)
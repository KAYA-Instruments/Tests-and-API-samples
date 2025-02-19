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
    parser.add_argument('--camera', type=str, default='Chameleon', help='Camera for test')
    parser.add_argument('--pixelFormat', type=str, default='Mono8', help='PixelFormat for test')
    parser.add_argument('--testPattern', type=str, default='FIXED',help='Pattern for camera image')
    return parser

def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)
##########
# Classes
##########
class StreamCallbackStruct:
    def __init__(self):
        self.firstFrame = []
        self.transformedImage = []
        self.secondFrame = []
        self.dataType = np
class Definitions:
    GainMatrix = ['RR', "GG", "BB"]
    OffsetMatrix = ["R0", "G0", "B0"]
    GainMatrixDefault = [1., 1., 1.]
    OffsetMatrixDefault = [0., 0., 0.]
##########
# Functions
##########
def streamCallbackFunction(buffHandle, userContext):
    if buffHandle == 0:
        return
    (KYFG_BufferGetInfo_status, pSize, pInfoSize, pInfoType) = KYFG_BufferGetInfo(
        buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_SIZE)  # SIZET
    (KYFG_BufferGetInfo_status, pInfoPTR, pInfoSize, pInfoType) = KYFG_BufferGetInfo(
        buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_BASE)  # PTR
    buffContent = numpy_from_data(pInfoPTR, pSize, userContext.dataType)
    if len(userContext.firstFrame) == 0:
        userContext.firstFrame = buffContent.copy()
    else:
        userContext.secondFrame = buffContent.copy()
    (status,) = KYFG_BufferToQueue(buffHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
def getDataType(pixelFormat: str):
    return np.uint8 if pixelFormat.endswith('8') else np.uint16
def numpy_from_data(buffData, buffSize, datatype):
    data_pointer= ctypes.cast(buffData, ctypes.c_char_p)
    buffer_from_memory = ctypes.pythonapi.PyMemoryView_FromMemory
    buffer_from_memory.restype = ctypes.py_object
    # buffer_from_memory.restype=ctypes.c_uint16
    buffer = buffer_from_memory(data_pointer, buffSize)
    return np.frombuffer(buffer, datatype)
    # return buffer
def color_transformation(frame, gainMatrix, offsetMatrix, pixelFormat):
    newFrame = [0 for i in range(len(frame))]
    bitDepth = getBitDepth(pixelFormat)
    for Ipixel in range(len(frame))[::3]:
        pixelsMatrix = [frame[Ipixel], frame[Ipixel+1], frame[Ipixel+2]]
        transformedPixel = np.dot(gainMatrix, pixelsMatrix) + offsetMatrix
        newFrame[Ipixel] = transformedPixel[0]
        newFrame[Ipixel + 1] = transformedPixel[1]
        newFrame[Ipixel + 2] = transformedPixel[2]
    for nextPixel in range(len(newFrame)):
        if newFrame[nextPixel] > bitDepth:
            newFrame[nextPixel] = bitDepth
    return newFrame
def getBitDepth(pixelFormat: str):
    if pixelFormat.endswith("8"):
        return pow(2, 8)-1
    else:
        bitness = int(pixelFormat[-2:])
        return pow(2, bitness)-1
def setTransformationValue(grabberHandle,key:str, val:float):
    KYFG_SetGrabberValueFloat(grabberHandle, f"ColorTransformation{key}", val)
def show_gain_control(grabberHandle):
    for i in range(len(Definitions.GainMatrix)):
        (status, value) = KYFG_GetGrabberValueFloat(grabberHandle, f"ColorTransformation{Definitions.GainMatrix[i]}")
        print(f"{Definitions.GainMatrix[i]}: {value}")
def show_offset_control(grabberHandle):
    for i in range(len(Definitions.OffsetMatrix)):
        (status, value) = KYFG_GetGrabberValueFloat(grabberHandle, f"ColorTransformation{Definitions.OffsetMatrix[i]}")
        print(f"{Definitions.OffsetMatrix[i]}: {value}")
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
    camera = args['camera']
    pixelFormat = args['pixelFormat']
    testPattern = args['testPattern']
    gain_full_matrix = np.array([[3., 0., 0.], [0., 3., 0.], [0., 0., 3.]])
    gain_matrix = [3., 3., 3.]
    offset_matrix = [3., 3., 3.]
    (grabberHandle,) = KYFG_Open(device_index)
    (status, camList) = KYFG_UpdateCameraList(grabberHandle)
    cameraHandle = None
    for cam in camList:
        (status, camInfo) = KYFG_CameraInfo2(cam)
        if camera in camInfo.deviceModelName:
            cameraHandle = cam
    if not cameraHandle:
        print(f"There is no camera {camera} on this grabber")
        return CaseReturnCode.NO_HW_FOUND
    (status, camInfo) = KYFG_CameraInfo2(cameraHandle)
    print(f'Camera {camInfo.deviceModelName} is found')
    (status, ) = KYFG_CameraOpen2(cameraHandle, None)
    (status, ) = KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "PixelFormat", pixelFormat)
    try:
        (status, ) = KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "VideoSourcePatternType", testPattern)
    except:
        (status, ) = KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "TestPattern", testPattern)
    KYFG_SetGrabberValueInt(grabberHandle, "CameraSelector", camList.index(cameraHandle))
    streamStruct = StreamCallbackStruct()
    streamStruct.dataType = getDataType(pixelFormat)
    for a in range(len(Definitions.GainMatrix)):
        setTransformationValue(grabberHandle, Definitions.GainMatrix[a], Definitions.GainMatrixDefault[a])
        setTransformationValue(grabberHandle, Definitions.OffsetMatrix[a], Definitions.OffsetMatrixDefault[a])
    print("1 Stream")
    for i in range(2):
        show_gain_control(grabberHandle)
        show_offset_control(grabberHandle)
        (status, streamHandle) = KYFG_StreamCreate(cameraHandle, 0)
        (status,) = KYFG_StreamBufferCallbackRegister(streamHandle, streamCallbackFunction, streamStruct)
        (status, pSize, size, infoType) = KYFG_StreamGetInfo(streamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_PAYLOAD_SIZE)
        number_of_buffers = [0 for i in range(16)]
        for iFrame in range(len(number_of_buffers)):
            (status,number_of_buffers[i]) = KYFG_BufferAllocAndAnnounce(streamHandle, pSize, 0)
        (status,) = KYFG_BufferQueueAll(streamHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_UNQUEUED, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
        (status,) = KYFG_CameraStart(cameraHandle, streamHandle, 1)
        time.sleep(2)
        (status,) = KYFG_CameraStop(cameraHandle)
        (status,) = KYFG_StreamBufferCallbackUnregister(streamHandle, streamCallbackFunction)
        (status,) = KYFG_StreamDelete(streamHandle)
        if i == 0:
            for a in range(len(Definitions.GainMatrix)):
                setTransformationValue(grabberHandle, Definitions.GainMatrix[a], gain_matrix[a])
                setTransformationValue(grabberHandle, Definitions.OffsetMatrix[a], offset_matrix[a])
            print('2 stream')
    for a in range(len(Definitions.GainMatrix)):
        setTransformationValue(grabberHandle, Definitions.GainMatrix[a], Definitions.GainMatrixDefault[a])
        setTransformationValue(grabberHandle, Definitions.OffsetMatrix[a], Definitions.OffsetMatrixDefault[a])
    print('To default')
    show_gain_control(grabberHandle)
    show_offset_control(grabberHandle)
    (status,) = KYFG_CameraClose(cameraHandle)
    (status,) = KYFG_Close(grabberHandle)
    streamStruct.transformedImage = color_transformation(streamStruct.firstFrame, gain_full_matrix, offset_matrix, pixelFormat)
    print(len(streamStruct.transformedImage), len(streamStruct.secondFrame))
    assert len(streamStruct.transformedImage) > 0 and len(streamStruct.secondFrame) > 0, 'Acquisition is not started'
    assert (streamStruct.transformedImage == streamStruct.secondFrame).all(), 'Images are not equals'
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

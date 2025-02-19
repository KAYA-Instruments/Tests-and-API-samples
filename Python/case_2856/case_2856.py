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
import pathlib
import queue
import matplotlib.pyplot as plt


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
    parser.add_argument('--camera', type=str, default="Chameleon", help='Camera')
    parser.add_argument('--width', type=int, default=1280, help='Width')
    parser.add_argument('--height', type=int, default=960, help='Height')
    parser.add_argument('--cameraPixelFormat', type=str, default="BayerRG8", help='cameraPixelFormat')
    parser.add_argument('--grabberPixelFormat', type=str, default="RGB8", help='grabberPixelFormat')
    parser.add_argument('--normal_expected_raw', type=str, default="bayerRG8_1280x960_before.raw",
                        help='normal_expected_raw')
    parser.add_argument('--debayered_expected_raw', type=str, default="bayerRG8_1280x960_after.raw",
                        help='debayered_expected_raw')
    return parser

def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)

class StreamStruct():
    def __init__(self):
        self.frame = []
        self.queue = queue.Queue()
        self.datatype = 0
        return

def Stream_callback_func(buffHandle, userContext):
    if (buffHandle == 0):
        return
    (KYFG_BufferGetInfo_status, pInfoBase, pInfoSize, pInfoType) = KYFG_BufferGetInfo(
        buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_BASE)
    (KYFG_BufferGetInfo_status, pSize, pInfoSize, pInfoType) = KYFG_BufferGetInfo(
        buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_SIZE)
    userContext.frame = numpy_from_data(pInfoBase, pSize, userContext.datatype).copy()
    userContext.queue.put(True)
    (status,) = KYFG_BufferToQueue(buffHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
    return

def numpy_from_data(buffData, buffSize, datatype):
    data_pointer= ctypes.cast(buffData, ctypes.c_char_p)
    buffer_from_memory = ctypes.pythonapi.PyMemoryView_FromMemory
    buffer_from_memory.restype = ctypes.py_object
    buffer = buffer_from_memory(data_pointer, buffSize)
    return np.frombuffer(buffer, datatype)

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
    width = args["width"]
    height = args["height"]
    expectedBeforeFile = pathlib.Path(__file__).parent.joinpath(args["normal_expected_raw"]).absolute()
    expectedAfterFile = pathlib.Path(__file__).parent.joinpath(args["debayered_expected_raw"]).absolute()
    cameraPixelFormat = args["cameraPixelFormat"]
    grabberPixelFormat = args["grabberPixelFormat"]
    camera = args['camera']
    datatype = np.uint8 if '8' in cameraPixelFormat else np.uint16
    with open(expectedBeforeFile, 'rb') as beforeFile:
        expectedBeforeFile_data = np.frombuffer(beforeFile.read(), dtype=datatype)
    with open(expectedAfterFile, 'rb') as afterFile:
        expectedAfterFile_data = np.frombuffer(afterFile.read(), dtype=datatype)
    print(f'expectedBeforeFile size: {len(expectedBeforeFile_data)}, expectedAfterFile size: {len(expectedAfterFile_data)}')
    (status, device_info) = KY_DeviceInfo(device_index)
    if device_info.m_Protocol != KY_DEVICE_PROTOCOL.KY_DEVICE_PROTOCOL_CoaXPress:
        return CaseReturnCode.COULD_NOT_RUN
    (grabberHandle,) = KYFG_Open(device_index)

    # Check Normal setting
    (CameraScan_status, camHandleArray) = KYFG_UpdateCameraList(grabberHandle)
    assert len(camHandleArray) > 0, 'There are no cameras on this grabber'
    cameraHandle = 0
    cameraIndex = 0
    for i, cam in enumerate(camHandleArray):
        (status, camInfo) = KYFG_CameraInfo2(cam)
        if camera in camInfo.deviceModelName:
            cameraHandle = cam
            cameraIndex = i
            print(f'Camera {camInfo.deviceModelName} found')
    if cameraHandle == 0:
        (status,) = KYFG_Close(grabberHandle)
        print(f'There in no camera {camera} on this grabber')
        return CaseReturnCode.NO_HW_FOUND
    (status,) = KYFG_CameraOpen2(cameraHandle, None)
    (status, camInfo) = KYFG_CameraInfo2(cameraHandle)
    print(f'Camera {camInfo.deviceModelName} is open')
    try:
        if KYFG_IsGrabberValueImplemented(grabberHandle, 'TriggerMode'):
            KYFG_SetGrabberValueEnum(grabberHandle, "TriggerMode", 0)
        if KYFG_IsCameraValueImplemented(cameraHandle, "TriggerMode"):
            KYFG_SetCameraValueEnum(cameraHandle, "TriggerMode", 0)
    except:
        pass
    (status,) = KYFG_SetCameraValueInt(cameraHandle, "Width", width)
    (status,) = KYFG_SetCameraValueInt(cameraHandle, "Height", height)
    if "Adimec" in camInfo.deviceVendorName:
        KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "TestImageSelector", "AdimecTestPattern")
    else:
        (status,) = KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "VideoSourceType", "File")
        (status,) = KYFG_SetCameraValueString(cameraHandle, "SourceFilePath", expectedBeforeFile.as_posix())
    (status,) = KYFG_SetGrabberValueInt(grabberHandle, "CameraSelector", cameraIndex)
    try:
        (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "PixelFormat", grabberPixelFormat)
    except:
        print(f'Incorrect grabber Pixel Format {grabberPixelFormat} for camera PixelFormat {cameraPixelFormat}')
        (status,) = KYFG_Close(grabberHandle)
        return CaseReturnCode.WRONG_PARAM_VALUE
    KYFG_SetGrabberValueEnum(grabberHandle, "DebayerMode", 0)
    (status, debayer_mode) = KYFG_GetGrabberValueEnum(grabberHandle, "DebayerMode")
    (status,grabberpfName) = KYFG_GetGrabberValueStringCopy(grabberHandle, "PixelFormat")
    (status,camerapfName) = KYFG_GetCameraValueStringCopy(cameraHandle, "PixelFormat")
    streamStruct = StreamStruct()
    streamStruct.datatype = datatype
    (status, streamHandle) = KYFG_StreamCreate(cameraHandle, 0)
    (status,) = KYFG_StreamBufferCallbackRegister(streamHandle, Stream_callback_func, streamStruct)
    buffersArray = [0 for i in range(16)]

    (status, payload_size, frameDataSize, pInfoType) = \
        KYFG_StreamGetInfo(streamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_PAYLOAD_SIZE)

    for i in range(len(buffersArray)):
        buffersArray[i] = KYFG_BufferAllocAndAnnounce(streamHandle, payload_size, 0)
    (status,) = KYFG_BufferQueueAll(streamHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_UNQUEUED,
                                    KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
    (status,) = KYFG_CameraStart(cameraHandle, streamHandle, 1)
    event = streamStruct.queue.get(timeout=15)
    # assert event, 'Acquisition is not started'
    time.sleep(3)
    (status,) = KYFG_CameraStop(cameraHandle)
    (status,) = KYFG_StreamBufferCallbackUnregister(streamHandle, Stream_callback_func)
    (status,) = KYFG_StreamDelete(streamHandle)
    (status,) = KYFG_CameraClose(cameraHandle)
    print(len(expectedAfterFile_data), len(streamStruct.frame))
    expected_frame = streamStruct.frame[width*3:-width*3]                       # NOTE! FOR HARDWARE DEBAYERING ONLY!
    real_frame = expectedAfterFile_data[width*3:-width*3]                       # First and last pixel line can contain incorrect values
    different = (expected_frame-real_frame).reshape(height-2, width, 3)         # we should ignore it
    (status,) = KYFG_Close(grabberHandle)
    assert (expected_frame == real_frame).all(), "Images are not equals"
    print(f'\nExiting from CaseRun({args}) with code SUCCESS...')
    print('IMAGES ARE EQUALS')
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

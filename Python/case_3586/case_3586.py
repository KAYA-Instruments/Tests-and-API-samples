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
from PIL import Image
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

    return parser

def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)

class StreamStruct:
    def __init__(self):
        self.callbackCount = 0
        self.images = []
        self.width = 0
        self.height = 0
        self.depth = 0

def streamCallbackFunction(buffHandle, userContext):
    if buffHandle == 0:
        return
    (KYFG_BufferGetInfo_status, pInfoPTR, pInfoSize, pInfoType) = KYFG_BufferGetInfo(
        buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_BASE)  # PTR
    (KYFG_BufferGetInfo_status, bufSize, pInfoSize, pInfoType) = KYFG_BufferGetInfo(
        buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_SIZE)  # SIZET
    # print(bufSize-8)
    acquired_image = numpy_from_data(pInfoPTR, bufSize-8, np.uint8).reshape(
        userContext.height, userContext.width, userContext.depth)
    # acquired_image = numpy_from_data(pInfoPTR, bufSize-8, np.uint8)
    userContext.images.append(acquired_image.copy())
    try:
        (status,) = KYFG_BufferToQueue(buffHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
    except:
        return
    userContext.callbackCount += 1

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

    (status, devInfo) = KY_DeviceInfo(device_index)
    if devInfo.m_Flags != KY_DEVICE_INFO_FLAGS.GENERATOR:
        print('Test can be started on Chameleon device only')
        print('devInfo.m_Flags = ', devInfo.m_Flags)
        return CaseReturnCode.COULD_NOT_RUN
    data_sample_folder = os.getenv('KAYA_VISION_POINT_SAMPLE_DATA')
    print(data_sample_folder)
    image_str = '/example_rgb_8bit.bmp'
    image = Image.open(data_sample_folder+image_str)
    image_array = np.array(image)
    is_chameleon_on_grabber = False
    error_count = 0
    (grabberHandle,) = KYFG_Open(device_index)
    (status, camList) = KYFG_UpdateCameraList(grabberHandle)

    for cameraHandle in camList:
        (status, camInfo) = KYFG_CameraInfo2(cameraHandle)
        if "Chameleon" in camInfo.deviceModelName:
            is_chameleon_on_grabber = True
        else:
            continue
        (status,) = KYFG_CameraOpen2(cameraHandle, None)

        buffers = [0 for i in range(16)]
        stream_struct = StreamStruct()
        (stream_struct.height, stream_struct.width, stream_struct.depth) = image_array.shape
        try:
            if KYFG_IsCameraValueImplemented(cameraHandle, "SimulationTriggerMode"):
                KYFG_SetCameraValueEnum(cameraHandle, "SimulationTriggerMode", 0)
        except:
            pass
        KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "PixelFormat", "RGB8")
        KYFG_SetCameraValueInt(cameraHandle, "Width", stream_struct.width)
        KYFG_SetCameraValueInt(cameraHandle, "Height", stream_struct.height)
        (status, streamHandle) = KYFG_StreamCreate(cameraHandle, 0)
        (status,) = KYFG_StreamBufferCallbackRegister(streamHandle, streamCallbackFunction, stream_struct)
        (status, payloadSize ,_ , _) = KYFG_StreamGetInfo(streamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_PAYLOAD_SIZE)
        for i in range(len(buffers)):
            (status, buffers[i]) = KYFG_BufferAllocAndAnnounce(streamHandle, payloadSize, 0)
        (status) = KYFG_LoadFileData(streamHandle, data_sample_folder+image_str, 'raw', 0)
        (status,) = KYFG_BufferQueueAll(streamHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_UNQUEUED, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
        (status,) = KYFG_CameraStart(cameraHandle, streamHandle, 0)
        time.sleep(2)
        (status,) = KYFG_CameraStop(cameraHandle)
        (status,) = KYFG_StreamBufferCallbackUnregister(streamHandle, streamCallbackFunction)
        (status,) = KYFG_StreamDelete(streamHandle)
        (status,) = KYFG_CameraClose(cameraHandle)
        for next_image in stream_struct.images:
            if not np.array_equal(next_image, image_array):
                print('images not equals')
                error_count += 1
            else:
                print('IMAGES ARE EQUALS')

    if not is_chameleon_on_grabber:
        print('There is no Chameleon on grabber')
        return CaseReturnCode.NO_HW_FOUND

    (status,) = KYFG_Close(grabberHandle)
    assert error_count == 0
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

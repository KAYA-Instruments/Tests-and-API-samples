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
import pathlib


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
    parser.add_argument('--patternType', type=str, default='YRAMP', help='Pattern type name')
    parser.add_argument('--pixelFormat', type=str, default='RGB8', help='Pixel format name')
    parser.add_argument('--duration', type=int, default=3, help='Pixel format name')
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
        self.callbackCounter = 0
        self.frames = []
##########
# Functions
#########
def StreamCallbackFunction(buffHandle, userConext):
    if buffHandle == 0:
        return
    (KYFG_BufferGetInfo_status, pInfoBase, pInfoSize, pInfoType) = KYFG_BufferGetInfo(
        buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_BASE)
    (KYFG_BufferGetInfo_status, pSize, pInfoSize, pInfoType) = KYFG_BufferGetInfo(
        buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_SIZE)
    buffContent = ctypes.string_at(pInfoBase, size=pSize)
    userConext.frames.append(buffContent)
    userConext.callbackCounter += 1
    try:
        (status,) = KYFG_BufferToQueue(buffHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
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
    (status, device_info) = KY_DeviceInfo(device_index)
    if device_info.m_Protocol != KY_DEVICE_PROTOCOL.KY_DEVICE_PROTOCOL_CoaXPress:
        print('Test could not run on this grabber')
    patternType = args['patternType']
    pixelFormat = args['pixelFormat']
    duration = args['duration']
    expected_image_file = pathlib.Path(__file__).parent.joinpath(f"{patternType}_{pixelFormat}.raw")
    assert expected_image_file.exists(), "expected_image_file is not exists"
    with expected_image_file.open('rb') as raw_file:
        expected_image_data = raw_file.read()
    (grabberHandle,) = KYFG_Open(device_index)
    (status, cameraList) = KYFG_UpdateCameraList(grabberHandle)
    cameraHandle = None
    for cam in cameraList:
        (status, camInfo) = KYFG_CameraInfo2(cam)
        if "Chameleon" in camInfo.deviceModelName:
            cameraHandle = cam
    if not cameraHandle:
        print('There is no Chameleon camera on this grabber')
        return CaseReturnCode.NO_HW_FOUND
    (status,) = KYFG_CameraOpen2(cameraHandle, None)
    try:
        if KYFG_IsGrabberValueImplemented(grabberHandle, 'TriggerMode'):
            KYFG_SetGrabberValueEnum(grabberHandle, "TriggerMode", 0)
        if KYFG_IsCameraValueImplemented(cameraHandle, "TriggerMode"):
            KYFG_SetCameraValueEnum(cameraHandle, "TriggerMode", 0)
        if KYFG_IsCameraValueImplemented(cameraHandle, "SimulationTriggerMode"):
            KYFG_SetCameraValueEnum(cameraHandle, "SimulationTriggerMode", 0)
    except:
        pass
    (status,) = KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "VideoSourcePatternType", patternType)
    (status,) = KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "PixelFormat", pixelFormat)
    (status,) = KYFG_SetCameraValueBool(cameraHandle, "VideoSourceMovingFrames", False)
    (status,) = KYFG_SetCameraValueInt(cameraHandle, "Width", 640)
    (status,) = KYFG_SetCameraValueInt(cameraHandle, "Height", 480)
    (status, streamHandle) = KYFG_StreamCreate(cameraHandle,0)
    streamStruct = StreamCallbackStruct()
    (status,) = KYFG_StreamBufferCallbackRegister(streamHandle, StreamCallbackFunction, streamStruct)
    (status, payload_size, _, _) = KYFG_StreamGetInfo(streamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_PAYLOAD_SIZE)
    buffers = [0 for i in range(16)]
    for iFrame in range(len(buffers)):
        (status, buffers[iFrame]) = KYFG_BufferAllocAndAnnounce(streamHandle, payload_size, 0)
    (status,) = KYFG_BufferQueueAll(streamHandle,KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_UNQUEUED,
                                    KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
    (status,) = KYFG_CameraStart(cameraHandle, streamHandle, 0)
    time.sleep(duration)
    (status,) = KYFG_CameraStop(cameraHandle)
    (status,) = KYFG_StreamBufferCallbackUnregister(streamHandle, StreamCallbackFunction)
    is_test_passed = True
    for iFrame in range(len(streamStruct.frames)):
        if streamStruct.frames[iFrame] != expected_image_data:
            print(f"Frame {iFrame} is not equal to expected frame")
            is_test_passed = False
    (status,) = KYFG_StreamDelete(streamHandle)
    (status,) = KYFG_CameraClose(cameraHandle)
    (status,) = KYFG_Close(grabberHandle)
    assert len(streamStruct.frames) > 0, 'Acquisition is not started'
    assert is_test_passed

    print("All frames is passed")
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

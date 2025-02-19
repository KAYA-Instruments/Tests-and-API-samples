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
    parser.add_argument('--fps', type=float, default=1000000.0, help='Frames per second')
    parser.add_argument('--numberOfFrames',type=int, default=200, help='Number of buffers')
    parser.add_argument('--links', type=int, default=1, help='Number of links')
    parser.add_argument('--speed', type=float,default=1.250, help='Speed in Gbps')

    return parser
def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)

class StreamInfoStruct:
    def __init__(self):
        self.callbackCount = 0
        self.instantsFps = []
        self.frameSize = []
        return

def Stream_callback_func(buffHandle, userContext):

    if (buffHandle == 0 ):
        return
    userContext.callbackCount += 1
    (KYFG_BufferGetInfo_status, pInfoFPS, pInfoSize, pInfoType) = KYFG_BufferGetInfo(
        buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_INSTANTFPS)
    (KYFG_BufferGetInfo_status, frameSize, pInfoSize, pInfoType) = KYFG_BufferGetInfo(
        buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_SIZE)

    userContext.instantsFps.append(pInfoFPS)
    userContext.frameSize.append(frameSize)
    try: (KYFG_BufferToQueue_status,) = KYFG_BufferToQueue(buffHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
    except: return
    return
def calculate_bandwidth(fps, frameSize):
    return ((fps*frameSize)/pow(1024, 3))*8
def expected_bandwidth(links, speed):
    return speed*0.8*links

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
    camera = 'Chameleon'
    fps = args['fps']
    links = args['links']
    speed = args['speed']
    numberOfFrames = args['numberOfFrames']
    (grabberHandle,) = KYFG_Open(device_index)
    (status, cameraList) = KYFG_UpdateCameraList(grabberHandle)
    print(f'Found {len(cameraList)} cameras')
    if len(cameraList) == 0:
        print('There are no cameras on this grabber')
        return CaseReturnCode.NO_HW_FOUND
    cameraHandle = 0
    for cam in cameraList:
        (status, camInfo) = KYFG_CameraInfo2(cam)
        if camera in camInfo.deviceModelName:
            cameraHandle = cam
    if cameraHandle == 0:
        print(f'There is no {camera} camera on this grabber')
        return CaseReturnCode.NO_HW_FOUND
    (status,) = KYFG_CameraOpen2(cameraHandle, None)
    (status,) = KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "ConnectionConfig", f"x{links}_CXP_{int(speed)}")
    (status,) = KYFG_SetCameraValueFloat(cameraHandle, "AcquisitionFrameRate", fps)
    (status, streamHandle) = KYFG_StreamCreate(cameraHandle, 0)
    streamStruct = StreamInfoStruct()
    (status,) = KYFG_StreamBufferCallbackRegister(streamHandle, Stream_callback_func, streamStruct)
    # Retrieve information about required frame buffer size and alignment
    (KYFG_StreamGetInfo_status, payload_size, frameDataSize, pInfoType) = \
        KYFG_StreamGetInfo(streamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_PAYLOAD_SIZE)

    (KYFG_StreamGetInfo_status, buf_allignment, frameDataAlignment, pInfoType) = \
        KYFG_StreamGetInfo(streamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_BUF_ALIGNMENT)
    streamBufferHandle = {}
    streamAlignedBuffer = {}
    number_of_buffers = 16
    # allocate memory for desired number of frame buffers
    for iFrame in range(number_of_buffers):
        streamAlignedBuffer[iFrame] = aligned_array(buf_allignment, c_ubyte, payload_size)
        # print("Address of alligned array: " + hex(addressof(streamAllignedBuffer[iFrame])))
        (status, streamBufferHandle[iFrame]) = KYFG_BufferAnnounce(streamHandle,
                                                                   streamAlignedBuffer[iFrame], None)
    (status,) = KYFG_BufferQueueAll(streamHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_UNQUEUED, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
    (status,) = KYFG_CameraStart(cameraHandle,streamHandle, 0)
    time.sleep(2)
    (status,) = KYFG_CameraStop(cameraHandle)
    (status,) = KYFG_StreamBufferCallbackUnregister(streamHandle, Stream_callback_func)
    (frameSize,) = KYFG_StreamGetSize(streamHandle)
    (status,) = KYFG_StreamDelete(streamHandle)
    streamStruct.instantsFps.pop(0)
    realFps = (sum(streamStruct.instantsFps)/len(streamStruct.instantsFps))
    real_bandwidth = calculate_bandwidth(realFps, frameSize)
    exp_bandwidth = expected_bandwidth(links, speed)
    result_in_percent = real_bandwidth*100/exp_bandwidth
    print(f'real_bandwidth = {round(real_bandwidth*8, 2)} Gbps')
    print(f'expected_bandwidth = {round(exp_bandwidth*8, 2)} Gbps')
    print(f'Real bandwidth is {round(result_in_percent, 2)}% from expected')
    (status,) = KYFG_Close(grabberHandle)
    assert result_in_percent >= 90.0, 'real_bandwidth on high speed there are errors'
    print(f'\nExiting from CaseRun({args}) with code 0...')
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

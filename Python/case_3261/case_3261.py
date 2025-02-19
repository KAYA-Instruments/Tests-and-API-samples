# Common KAYA imports DO NOT EDIT!!!
import sys
import os
import argparse
sys.path.insert(0, os.environ['KAYA_VISION_POINT_PYTHON_PATH'])
from KYFGLib import *

# Common Case imports DO NOT EDIT!!!
from enum import IntEnum  # for CaseReturnCode

# additional imports required by particular case, ADD CASE SPECIFIC IMPORTS UNDER THIS LINE:
import shlex
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
    parser.add_argument('--number_of_frames', type=int, default=100, help='number of frames')
    parser.add_argument('--cameraModel', default='Chameleon', type=str, help='Camera model')
    parser.add_argument('--pixelFormat', default='Mono8', type=str, help='pixelFormat for test')
    return parser

def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)
def is_approximately_equal(num1, num2, tolerance_percent):
    tolerance = tolerance_percent / 100.0
    diff = abs(num1 - num2)
    avg = (abs(num1) + abs(num2)) / 2.0
    return diff <= avg * tolerance

def streamCallbackFunction(buffHandle, userContext):
    if buffHandle == 0:
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
    cameraModel = args['cameraModel']
    number_of_frames = args['number_of_frames']
    pixelFormat = args['pixelFormat']
    first_packet_counter = None
    second_packet_counter = None
    for i in range(2):
        (grabberHandle,) = KYFG_Open(device_index)
        if i == 0:
            KYFG_SetGrabberValueInt(grabberHandle, 'StreamPacketDataSize', 8192)
        else:
            KYFG_SetGrabberValueInt(grabberHandle, 'StreamPacketDataSize', 4096)
        (status, cameraList) = KYFG_UpdateCameraList(grabberHandle)
        assert len(cameraList) > 0, 'There are no cameras on this grabber'
        cameraHandle = None
        for cam in cameraList:
            (status, camInfo) = KYFG_CameraInfo2(cam)
            if cameraModel in camInfo.deviceModelName:
                cameraHandle = cam
        assert cameraHandle is not None, f'Camera {cameraModel} not Found'

        (status, packetDataSize) = KYFG_GetGrabberValueInt(grabberHandle, 'StreamPacketDataSize')
        print("StreamPacketDataSize = ", packetDataSize)
        (status,) = KYFG_CameraOpen2(cameraHandle, None)
        (status,) = KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "PixelFormat", pixelFormat)
        KYFG_SetCameraValueInt(cameraHandle, "Width", 4096)
        (status, fps) = KYFG_GetCameraValueFloat(cameraHandle, "AcquisitionFrameRate")
        # stream Creation
        (status, streamHandle) = KYFG_StreamCreate(cameraHandle, 0)
        (status,) = KYFG_StreamBufferCallbackRegister(streamHandle, streamCallbackFunction, None)
        # Retrieve information about required frame buffer size and alignment
        (status, payload_size, _, _) = KYFG_StreamGetInfo(streamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_PAYLOAD_SIZE)
        (status, buf_allignment, _, _) = KYFG_StreamGetInfo(streamHandle,
                                                            KY_STREAM_INFO_CMD.KY_STREAM_INFO_BUF_ALIGNMENT)
        # allocate memory for desired number of frame buffers
        streamBufferHandle = [0 for i in range(number_of_frames)]
        streamAllignedBuffer = [0 for i in range(number_of_frames)]
        for iFrame in range(len(streamBufferHandle)):
            streamAllignedBuffer[iFrame] = aligned_array(buf_allignment, c_ubyte, payload_size)
            # print("Address of alligned array: " + hex(addressof(streamAllignedBuffer[iFrame])))
            (status, streamBufferHandle[iFrame]) = KYFG_BufferAnnounce(streamHandle,
                                                                       streamAllignedBuffer[iFrame], None)

        (status,) = KYFG_BufferQueueAll(streamHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_UNQUEUED,
                                        KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
        (status,) = KYFG_CameraStart(cameraHandle, streamHandle, number_of_frames)
        time.sleep((number_of_frames/fps) + 1)
        (status,) = KYFG_CameraStop(cameraHandle)
        (status,) = KYFG_SetGrabberValueInt(grabberHandle, "CameraSelector", cameraList.index(cameraHandle))
        (_, RXPacketCounter) = KYFG_GetGrabberValueInt(grabberHandle, 'RXPacketCounter')
        print("RXPacketCounter = ", RXPacketCounter)
        if i == 0:
            first_packet_counter = RXPacketCounter
        else:
            second_packet_counter = RXPacketCounter
        (_, RXFrameCounter) = KYFG_GetGrabberValueInt(grabberHandle, 'RXFrameCounter')
        print("RXFrameCounter = ", RXFrameCounter)
        (status,) = KYFG_StreamBufferCallbackUnregister(streamHandle, streamCallbackFunction)
        (status,) = KYFG_StreamDelete(streamHandle)
        (status,) = KYFG_CameraClose(cameraHandle)

        (status,) = KYFG_Close(grabberHandle)
    print("first_packet_counter = ", first_packet_counter)
    print("second_packet_counter = ", second_packet_counter)
    assert is_approximately_equal(first_packet_counter, second_packet_counter/2, 2)
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
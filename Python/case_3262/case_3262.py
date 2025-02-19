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
    parser.add_argument('--camera', default='Iron2020eM', type=str, help='CameraModelName for test')
    return parser

def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)


camHandleArray = {}


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
    camera=args['camera']


    (grabberHandle,) = KYFG_Open(device_index)
    (status, cameraList) = KYFG_UpdateCameraList(grabberHandle)
    if len(cameraList) == 0:
        print('There are no cameras on this grabber')
        return CaseReturnCode.NO_HW_FOUND
    cameraIndex = -1
    for cameraHandle in cameraList:
        (status, cameraInfo) = KYFG_CameraInfo2(cameraHandle)
        if camera in cameraInfo.deviceModelName:
            cameraIndex = cameraList.index(cameraHandle)
    print('Camera index', cameraIndex)
    if cameraIndex < 0:
        print(f'There are no camera {camera} on this grabber')
        return CaseReturnCode.NO_HW_FOUND
    start_read_buffer = []
    (status, size) = KYFG_DeviceDirectHardwareRead(grabberHandle, 0x402064, start_read_buffer, 4)
    #assert start_read_buffer[0] == 1, f'Wrong address or value of start_read_buffer: {start_read_buffer}'
    write_buffer = [0 for i in range(4)]
    (status, size) = KYFG_DeviceDirectHardwareWrite(grabberHandle, 0x402064, write_buffer)
    buffer_after_set = []
    (status, size) = KYFG_DeviceDirectHardwareRead(grabberHandle, 0x402064, buffer_after_set, 4)
    assert write_buffer == buffer_after_set, f'Wrong buffer write: write_buffer {write_buffer}, buffer_after_set {buffer_after_set}'

    (status,) = KYFG_SetGrabberValueInt(grabberHandle, "CameraSelector", cameraIndex)
    (status,) = KYFG_SetGrabberValueInt(grabberHandle, "Image1StreamID", 9)
    (status, cameraInfo) = KYFG_CameraInfo2(cameraList[cameraIndex])

    (status, cameraParams) = KYFG_CameraScanEx(grabberHandle, bRetainOpenCameras=False)
    assert len(cameraParams.pCamHandleArray) == len(cameraList), "Error while second camera detection"
    (status,) = KYFG_SetGrabberValueInt(grabberHandle, "CameraSelector", cameraIndex)
    (status,) = KYFG_CameraOpen2(cameraParams.pCamHandleArray[cameraIndex], None)
    (status, streamHandle) = KYFG_StreamCreateAndAlloc(cameraParams.pCamHandleArray[cameraIndex], 16, 0)
    (status,) = KYFG_CameraStart(cameraParams.pCamHandleArray[cameraIndex], streamHandle, 16)
    time.sleep(3)
    (status,) = KYFG_CameraStop(cameraParams.pCamHandleArray[cameraIndex])
    (status, RXPacketCounter) = KYFG_GetGrabberValueInt(grabberHandle, "RXPacketCounter")
    (status, DropStreamIdCounter) = KYFG_GetGrabberValueInt(grabberHandle, "DropStreamIdCounter")
    print('RXPacketCounter', RXPacketCounter)
    print('DropStreamIdCounter', DropStreamIdCounter)
    (status,) = KYFG_StreamDelete(streamHandle)

    (status,) = KYFG_CameraClose(cameraParams.pCamHandleArray[cameraIndex])
    (status,) = KYFG_Close(grabberHandle)
    assert RXPacketCounter==0 and DropStreamIdCounter>0, "First test doesn't pass"
    print('First test passed')
    (grabberHandle,) = KYFG_Open(device_index)
    (status,) = KYFG_SetGrabberValueInt(grabberHandle, "CameraSelector", cameraIndex)
    camera_stream_id = cameraInfo.stream_id
    KYFG_SetGrabberValueInt(grabberHandle, "Image1StreamID", camera_stream_id)
    (status, cameraList) = KYFG_UpdateCameraList(grabberHandle)
    (status, cameraInfo) = KYFG_CameraInfo2(cameraList[cameraIndex])
    (status, cameraParams) = KYFG_CameraScanEx(grabberHandle, bRetainOpenCameras=False)
    (status,) = KYFG_CameraOpen2(cameraParams.pCamHandleArray[cameraIndex], None)
    (status, streamHandle) = KYFG_StreamCreateAndAlloc(cameraParams.pCamHandleArray[cameraIndex], 16, 0)
    (status,) = KYFG_CameraStart(cameraParams.pCamHandleArray[cameraIndex], streamHandle, 16)
    time.sleep(3)
    (status,) = KYFG_CameraStop(cameraParams.pCamHandleArray[cameraIndex])
    (status, RXPacketCounter) = KYFG_GetGrabberValueInt(grabberHandle, "RXPacketCounter")
    (status, DropPacketCounter) = KYFG_GetGrabberValueInt(grabberHandle, "DropStreamIdCounter")
    KYFG_SetGrabberValueInt(grabberHandle, "Image1StreamID", -1)
    (status,) = KYFG_StreamDelete(streamHandle)
    (status,) = KYFG_CameraClose(cameraParams.pCamHandleArray[cameraIndex])
    print('RXPacketCounter', RXPacketCounter)
    print('DropPacketCounter',DropPacketCounter)

    (status, size) = KYFG_DeviceDirectHardwareWrite(grabberHandle, 0x402064, start_read_buffer)
    (status,) = KYFG_Close(grabberHandle)
    assert RXPacketCounter>0 and DropPacketCounter==0, 'Second test not pass'
    print(f'\nExiting from CaseRun({args}) with code 0...')
    return CaseReturnCode.SUCCESS


# The flow starts here
if __name__ == "__main__":
    # try:
        args_ = ParseArgs()
        return_code = CaseRun(args_)
        print(f'Case return code: {return_code}')
    # except Exception as ex:
    #     print(f"Exception of type {type(ex)} occurred: {str(ex)}")
    #     exit(-200)
    #
    # exit(return_code)
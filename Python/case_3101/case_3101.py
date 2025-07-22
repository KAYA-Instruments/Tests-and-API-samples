# Common KAYA imports DO NOT EDIT!!!
import sys
import os
import argparse
sys.path.insert(0, os.environ['KAYA_VISION_POINT_PYTHON_PATH'])
from KYFGLib import *

# Common Case imports DO NOT EDIT!!!
from enum import IntEnum  # for CaseReturnCode

# additional imports required by particular case, ADD CASE SPECIFIC IMPORTS UNDER THIS LINE:
# For example:
# import numpy as np
# import cv2
# from numpngw import write_png
import subprocess
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
    parser.add_argument('--number_of_tests', type=int, default=20, help='Number of camera start/stop in a loop')
    parser.add_argument('--num_of_frames', type=int, default=10)
    parser.add_argument('--sleep_after_camera_start', type=float, default=0.3)

    return parser


def Reset_Grabber(grabberHandle):
    pass
    # Grabber initialization for this specific test


def Reset_camera(cameraHandle):
    pass
    # Camera initialization for this specific test



def pipes_number(pid):
    command: str = "lsof -p {0}|grep pipe|wc -l".format(str(pid))
    p = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True, universal_newlines=True)
    res = p.stdout.read()
    retcode = p.wait()
    return int(res)


def ConnectToCamera(handle):
    """Connect to camera"""
    (status, camHandleArray) = KYFG_UpdateCameraList(handle)
    if len(camHandleArray) == 0:
        print("Please, connect at least one camera and restart test")
        return
    else:
        assert camHandleArray[0] > 0
        cams_num = len(camHandleArray)
        print("\nFound " + str(cams_num) + " cameras")
    return camHandleArray[0]


def Stream_callback_func(buffHandle, userContext):
    if buffHandle == 0:
        Stream_callback_func.copyingDataFlag = 0
        return
    print('Good callback streams buffer handle: ' + str(buffHandle))
    (KYFG_BufferToQueue_status,) = KYFG_BufferToQueue(buffHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
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

    # Other parameters used by this particular case
    system_platform = platform.system().lower()
    if system_platform == 'windows':
        print('This test case is for Linux OS only')
        return CaseReturnCode.WRONG_PARAM_VALUE

    num_of_frames = args["num_of_frames"]
    number_of_tests = args["number_of_tests"]
    sleep_after_camera_start = args["sleep_after_camera_start"]

    # Open selected PCI device (grabber)
    (grabber_handle,) = KYFG_Open(device_index)
    device_info = device_infos[device_index]
    print(f'Open [{device_index}]: (PCI {device_info.nBus}:{device_info.nSlot}:{device_info.nFunction})"{device_info.szDeviceDisplayName}"')
    (status, tested_dev_info) = KY_DeviceInfo(device_index)
    print("Device " + str(device_index) + " is tested: " + tested_dev_info.szDeviceDisplayName)

    # Connect and open camera
    camera_handle = ConnectToCamera(grabber_handle)
    (cam_open_status,) = KYFG_CameraOpen2(camera_handle, None)

    # Here must be KYFG_SetCameraValue(), KYFG_SetGrabberValue() if it need

    # Create stream and assign appropriate runtime acquisition callback function
    (status, buff_handle) = KYFG_StreamCreate(camera_handle, 0)
    (status,) = \
        KYFG_StreamBufferCallbackRegister(buff_handle, Stream_callback_func, 0)
        
    # Retrieve information about required frame buffer size and alignment
    (status, payload_size, frameDataSize, pInfoType) = \
        KYFG_StreamGetInfo(buff_handle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_PAYLOAD_SIZE)
    for iFrame in range(num_of_frames):
        (status, bufferhandle) = KYFG_BufferAllocAndAnnounce(buff_handle, payload_size, 0)

    # Get process PID
    pid = os.getpid()

    # Get pipes quantity before camera start
    pipes_num_first = pipes_number(pid)
    for i in range(number_of_tests):
        (status,) = \
            KYFG_BufferQueueAll(buff_handle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_UNQUEUED, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
        (status,) = KYFG_CameraStart(camera_handle, buff_handle, 0)
        time.sleep(sleep_after_camera_start)
        (status,) = KYFG_CameraStop(camera_handle)
        print(" Start/Stop " + str(i + 1) + " is ended.")
    print('CameraStop')

    # Get pipes quantity after camera stop
    pipes_num_second = pipes_number(pid)
    if number_of_tests < 0:
        pipes_num_second = -100

    # Close processing
    (CallbackRegister_status,) = KYFG_StreamBufferCallbackUnregister(buff_handle, Stream_callback_func)
    (KYFG_StreamDelete_status,) = KYFG_StreamDelete(buff_handle)
    (status,) = KYFG_CameraClose(camera_handle)
    (KYFG_Close_status,) = KYFG_Close(grabber_handle)

    print(f'QTY of pipes at the start: {pipes_num_first}')
    print(f'QTY of pipes at the stop:  {pipes_num_second}')
    assert pipes_num_second == pipes_num_first, 'the number of pipes not the same before KYFG_CameraStart and after KYFG_CameraStop'

    print(f'\nExiting from CaseRun({args}) with code 0...')
    return CaseReturnCode.SUCCESS


def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)


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

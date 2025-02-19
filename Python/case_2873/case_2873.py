# Common KAYA imports DO NOT EDIT!!!
import sys
import os
import argparse
sys.path.insert(0, os.environ['KAYA_VISION_POINT_PYTHON_PATH'])
from KYFGLib import *

# Common Case imports DO NOT EDIT!!!
from enum import IntEnum  # for CaseReturnCode

# additional imports required by particular case, ADD CASE SPECIFIC IMPORTS UNDER THIS LINE:

###################### Defines ####################################
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
    parser.add_argument('--number_of_tests', type=int, default=20,
                        help='Number of camera start/stop in a loop')
    return parser
################################## Main #################################################################

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

    number_of_tests = args["number_of_tests"]
    # Connect to grabber
    handle = ConnectToDevice(device_index)
    (status, tested_dev_info) = KY_DeviceInfo(device_index)
    print("Device " + str(device_index) + " is tested: " + tested_dev_info.szDeviceDisplayName)

    # Connect to camera
    camera_handle = ConnectToCamera(handle)

    for i in range(number_of_tests):
        # Camera open and start
        (cam_open_status,) = KYFG_CameraOpen2(camera_handle, None)
        try:
            if KYFG_IsGrabberValueImplemented(handle, 'TriggerMode'):
                KYFG_SetGrabberValueEnum(handle, "TriggerMode", 0)
            if KYFG_IsCameraValueImplemented(camera_handle, "TriggerMode"):
                KYFG_SetCameraValueEnum(camera_handle, "TriggerMode", 0)
            if KYFG_IsCameraValueImplemented(camera_handle, "SimulationTriggerMode"):
                KYFG_SetCameraValueEnum(camera_handle, "SimulationTriggerMode", 0)
        except:
            pass
        (status, buffHandle) = KYFG_StreamCreateAndAlloc(camera_handle, 16, 0)
        (status,) = KYFG_CameraStart(camera_handle, buffHandle, 0)

        # Camera stop and close
        (status,) = KYFG_CameraStop(camera_handle)
        assert_nothing_dropped(camera_handle)
        (status,) = KYFG_CameraClose(camera_handle)

        print(" Start/Stop " + str(i) + " is ended.")
    if (handle != 0):
        (KYFG_Close_status,) = KYFG_Close(handle)
    print("Test is ended.")
    return CaseReturnCode.SUCCESS

def ConnectToDevice(deviceindex):
    """Connect to grabber"""
    (connected_fghandle,) = KYFG_Open(deviceindex)
    print("Good connection to device " + str(deviceindex) + ", handle= " + str(connected_fghandle))
    return connected_fghandle

def ConnectToCamera(handle):
    """Connect to camera"""
    (status, camHandleArray) = KYFG_UpdateCameraList(handle)
    if len(camHandleArray) == 0:
        print("Please, connect at least one camera and restart test")
        return
    else:
        assert camHandleArray[0] > 0
        cams_num = len(camHandleArray)
        print("\nFound " + str(cams_num) + " cameras:")
    return camHandleArray[0]

def assert_nothing_dropped(camera_handle):
    (status, crc_errors) = KYFG_GetGrabberValue(camera_handle, "CRCErrorCounter")
    assert crc_errors == 0, f"CRCErrorCounter:{crc_errors}"
    (status, dropped_packets) = KYFG_GetGrabberValue(camera_handle, "DropPacketCounter")
    assert dropped_packets == 0, f"DropPacketCounter:{dropped_packets}"
    (status, dropped_frames) = KYFG_GetGrabberValue(camera_handle, "DropFrameCounter")
    assert dropped_frames == 0, f"DropFrameCounter:{dropped_frames}"

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


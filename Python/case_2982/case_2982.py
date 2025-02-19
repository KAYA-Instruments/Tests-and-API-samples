# Common KAYA imports DO NOT EDIT!!!
import sys
import os
import argparse
sys.path.insert(0, os.environ['KAYA_VISION_POINT_PYTHON_PATH'])
from KYFGLib import *

# Common Case imports DO NOT EDIT!!!
from enum import IntEnum  # for CaseReturnCode

# additional imports required by particular case, ADD CASE SPECIFIC IMPORTS UNDER THIS LINE:
import subprocess
camHandleArray = {}
camHandleArray2 = {}


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
    parser.add_argument('--instance', type=int, default=0, help='Camera index')

    return parser


def run_new_instance(device_index):
    if sys.version_info.major == 3:
        instance_process = subprocess.Popen(
            ["python3", f"{__file__}", '--unattended', "--deviceIndex", f"{str(device_index)}", "--instance", "1"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=True
        )
    else:
        instance_process = subprocess.Popen(
            ["python", f"{__file__}", "--deviceIndex", f"{str(device_index)}", "--instance", "1"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=True
        )
    instance_process.communicate()
    return instance_process.returncode








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

    (status, version) = KY_GetSoftwareVersion()
    if version.Major < 6:
        print('\nRequired hardware not found')
        return CaseReturnCode.NO_HW_FOUND
    
    is_instance = int(args.get("instance"))
    
    # Open selected PCI device
    (status, device_info) = KY_DeviceInfo(device_index)
    if device_info.m_Protocol != KY_DEVICE_PROTOCOL.KY_DEVICE_PROTOCOL_CoaXPress:
        print('Test could not run on this grabber')
        return CaseReturnCode.COULD_NOT_RUN
    (grabberHandle,) = KYFG_Open(device_index)
    #try:
    #    (status, isSharingSupported) = KYFG_GetGrabberValueInt(grabberHandle, 'SWCapable_InterProcessSharing_Imp')
    #    if not isSharingSupported:
    #        print('Grabber sharing is not supported on this device')
    #        (status,) = KYFG_Close(grabberHandle)
    #        return CaseReturnCode.COULD_NOT_RUN
    #except:
    #    print('Grabber sharing is not supported on this device')
    #    (status,) = KYFG_Close(grabberHandle)
    #    return CaseReturnCode.COULD_NOT_RUN
    # Check Normal setting
    (CameraScan_status, camHandleArray[device_index]) = KYFG_UpdateCameraList(grabberHandle)
    assert len(camHandleArray[device_index])!=0, 'There are no cameras on this device'
    cams_num = len(camHandleArray[device_index])

    cameraHandle = camHandleArray[device_index][0]
    (Status, camInfo) = KYFG_CameraInfo2(cameraHandle)
    # Open camera on first instance
    KYFG_CameraOpen2(cameraHandle, None)
    # Open the second instance and try to open the same camera. The camera should not be opened
    if not is_instance:
        instance_returncode = run_new_instance(device_index)
        assert instance_returncode != 0, f'The camera {camInfo.deviceModelName} can be opened on more than one instance'
        # Close the camera on first instance
        KYFG_CameraClose(cameraHandle)
        # Open the second instance and try to open the same camera. The camera should be opened
        instance_returncode = run_new_instance(device_index)
        assert instance_returncode == 0, f'The camera {camInfo.deviceModelName} failed to open'

    KYFG_Close(grabberHandle)
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

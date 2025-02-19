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
import threading
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
    parser.add_argument('--instance', type=int, default=0, help='Camera index')
    return parser


def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)
kill_instance_1 = False
instance_process = None
def run_new_instance(device_index):
    global instance_process
    if sys.version_info.major == 3:
        instance_process = subprocess.Popen(
            ["python3", f"{__file__}", "--deviceIndex", f"{str(device_index)}", "--instance", "1"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,
            universal_newlines=True
        )
    else:
        instance_process = subprocess.Popen(
            ["python", f"{__file__}", "--deviceIndex", f"{str(device_index)}", "--instance", "1"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,
            universal_newlines=True
        )
    instance_process.communicate()
    counter = 0
    while True:
        if kill_instance_1 == True:
            instance_process.terminate()
            break
        else:
            time.sleep(1)
            counter += 1
            if counter==200:
                instance_process.terminate()
                break

    return instance_process




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
    is_instance = args["instance"]
    (grabberHandle,) = KYFG_Open(device_index)
    try:
        (status, isSharingSupported) = KYFG_GetGrabberValueInt(grabberHandle, 'FW_Dma_Capable_QueuedBuffers_Imp')
    except:
        print('Grabber sharing is not supported on this device')
        (status,) = KYFG_Close(grabberHandle)
        return CaseReturnCode.NO_HW_FOUND
    if isSharingSupported == 0:
        print('Grabber sharing is not supported on this FW')
        print('\nPlease update your DeviceFirmwareVersion to 6.1.1 and upper')
        return CaseReturnCode.NO_HW_FOUND
    global kill_instance_1
    test_failed = False
    (CameraScan_status, camHandleArray) = KYFG_UpdateCameraList(grabberHandle)
    cams_num = len(camHandleArray)

    if cams_num < 2:
        return CaseReturnCode.NO_HW_FOUND
    elif cams_num > 2:
        camHandleArray = camHandleArray[0:2]
    (Status, camInfo) = KYFG_CameraInfo2(camHandleArray[is_instance])
    print(f'Camera for instance {is_instance}',camInfo.deviceModelName)
    # Open camera on N instance
    (status,) = KYFG_CameraOpen2(camHandleArray[is_instance], None)
    (status, streamHandle) = KYFG_StreamCreateAndAlloc(camHandleArray[is_instance], 16, 0)
    (status,) = KYFG_CameraStart(camHandleArray[is_instance], streamHandle,0)
    if is_instance == 1:
        while True:
            time.sleep(1)
    if is_instance == 0:
        new_instance = threading.Thread(target=run_new_instance, args=[device_index])
        new_instance.start()
        time.sleep(10)
        #  Stop and close camera 0 in subprocess 0
        (status,) = KYFG_CameraStop(camHandleArray[is_instance])
        (status,) = KYFG_StreamDelete(streamHandle)
        (status,) = KYFG_CameraClose(camHandleArray[is_instance])
        # Try connecting from subprocess 0 to camera 1;
        try:
            (status,) = KYFG_CameraOpen2(camHandleArray[1], None)
            print('1 Try connecting from subprocess 0 to camera 1; result: success')
            test_failed = True
            (status) = KYFG_Close(grabberHandle)
            assert test_failed == False, 'Test not passed'
        except Exception as ex:
            print('1 Try connecting from subprocess 0 to camera 1; result: decline')
            print(type(ex), str(ex))
        kill_instance_1 = True
        time.sleep(3)
        try:
            (status,) = KYFG_CameraOpen2(camHandleArray[1], None)
            print('2 Try connecting from subprocess 0 to camera 1; result: success')
            (status,) = KYFG_CameraClose(camHandleArray[1])
        except:
            print('2 Try connecting from subprocess 0 to camera 1; result: decline')
            assert test_failed == False, 'Test not passed'
    (status,) = KYFG_Close(grabberHandle)
    print(f'\nExiting from CaseRun({args}) with code 0...')
    return CaseReturnCode.SUCCESS



# The flow starts here
if __name__ == "__main__":
    try:
        args_ = ParseArgs()
        return_code = CaseRun(args_)
        try:
            deviceIndex = args_['deviceIndex']
        except:
            pass
        print(f'Case return code: {return_code}')
    except Exception as ex:
        print(f"Exception of type {type(ex)} occurred: {str(ex)}")
        exit(-200)

    exit(return_code)
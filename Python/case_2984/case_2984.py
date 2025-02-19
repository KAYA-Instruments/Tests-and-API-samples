# Common KAYA imports DO NOT EDIT!!!
import sys
import os
import argparse
from threading import Thread
sys.path.insert(0, os.environ['KAYA_VISION_POINT_PYTHON_PATH'])
from KYFGLib import *

# Common Case imports DO NOT EDIT!!!
from enum import IntEnum  # for CaseReturnCode

# additional imports required by particular case, ADD CASE SPECIFIC IMPORTS UNDER THIS LINE:
import subprocess
import pathlib
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
    return parser


def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)


threads_results = {}


def startNewInstance(VP_file, JS_file, deviceIndex, instance, timeOut, number_of_cameras):
    global threads_results
    command = [f"{VP_file}", '--guiscript', f"{JS_file}", '--guiscriptParameters',
               f"--deviceIndex {deviceIndex} --instance {instance} --number_of_cameras {str(number_of_cameras)}"]
    process = subprocess.Popen(command, timeOut, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               universal_newlines=True)
    (stdout, stderr) = process.communicate()
    process_return_code = process.returncode
    process_result = {'return_code': process_return_code, 'output': stdout + stderr}
    threads_results[f'instance_{instance}'] = process_result

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
    global threads_results
    (grabberHandle,) = KYFG_Open(device_index)
    (status, cameraList) = KYFG_UpdateCameraList(grabberHandle)
    print(len(cameraList), "cameras detected")
    (status,) = KYFG_Close(grabberHandle)
    if len(cameraList) < 2:
        print('At least 2 cameras needed for this test')
        return CaseReturnCode.NO_HW_FOUND
    vision_point_env_name = "KAYA_VISION_POINT_APP_PATH"
    vision_point_exe = pathlib.Path(os.environ.get(vision_point_env_name)).joinpath('VisionPoint.exe')
    case_number = pathlib.Path(__file__).name.replace(".py", "")
    js_file_name = case_number + ".js"
    js_case_file = pathlib.Path(__file__).parent.joinpath(js_file_name)
    threads_list = []
    for nextInstance in range(len(cameraList)):
        sleepTime = len(cameraList) * 40000 if nextInstance == 0 else 10000
        timeOut = int(sleepTime/1000)+30 if nextInstance == 0 else 50
        new_thread = Thread(target=startNewInstance, args=[vision_point_exe,
                                                           js_case_file,
                                                           device_index,
                                                           nextInstance,
                                                           timeOut,
                                                           len(cameraList)])
        threads_list.append(new_thread)
        new_thread.start()
        time.sleep(40)
    for thread in threads_list:
        thread.join()
    for a, b in threads_results.items():
        print(a, b)
    instance_0_output = threads_results["instance_0"]["output"]
    assert "Case return code: 0" in instance_0_output, 'Test not Passed'
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

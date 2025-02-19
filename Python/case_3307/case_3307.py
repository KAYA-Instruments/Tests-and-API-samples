# Common KAYA imports DO NOT EDIT!!!
import sys
import os
import argparse
sys.path.insert(0, os.environ['KAYA_VISION_POINT_PYTHON_PATH'])
from KYFGLib import *

# Common Case imports DO NOT EDIT!!!
from enum import IntEnum  # for CaseReturnCode

# additional imports required by particular case, ADD CASE SPECIFIC IMPORTS UNDER THIS LINE:
import threading
import subprocess


def CaseArgumentParser():
    parser = argparse.ArgumentParser()
    # Common arguments for all cases DO NOT EDIT!!!
    parser.add_argument('--unattended', default=True, action='store_true', help='Do not interact with user')
    parser.add_argument('--no-unattended', dest='unattended', action='store_false')
    parser.add_argument('--deviceList', default=False, action='store_true',
                        help='Print list of available devices and exit')
    parser.add_argument('--deviceIndex', type=int, default=0,
                        help='Index of PCI device to use, '
                             'run this script with "--deviceList" to see available devices and exit')
    # Other arguments needed for this specific case, PARSE CASE SPECIFIC ARGUMENTS UNDER THIS LINE:
    parser.add_argument('--mainThread', type=str, default='True', help='Thread starts other threads')
    parser.add_argument('--device_index_for_thread', type=int, help='Thread starts other threads')
    return parser


def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)
threadsReturnCodes={}
def backgroundTask(device_index):
    instance_process = subprocess.Popen(
        ["python", f"{__file__}", '--device_index_for_thread', f'{device_index}', "--mainThread", "False"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        close_fds=True)
    stdout_output, stderr_output = instance_process.communicate()
    print(stdout_output.decode())
    print(stderr_output)
    return_code = instance_process.returncode
    (status, devInfo) = KY_DeviceInfo(device_index)
    print(f'Return Code {return_code} for {devInfo.szDeviceDisplayName}')
    threadsReturnCodes[f'{devInfo.szDeviceDisplayName}'] = return_code
    return return_code

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

    # Create flags for all of threads
    mainThread=args['mainThread']

    if mainThread == 'True':
        # flags = [threading.Event() for _ in range(infosize_test)]
        background_threads = []
        for i in range(infosize_test):
            thread = threading.Thread(target=backgroundTask, args=(i,))
            background_threads.append(thread)
            thread.start()
    if mainThread == 'False':
        device_index_for_thread = args['device_index_for_thread']
        print('device_index_for_thread', device_index_for_thread)
        (status, grabInfo) = KY_DeviceInfo(device_index_for_thread)
        if 'Chameleon' in grabInfo.szDeviceDisplayName:
            print(f'{grabInfo.szDeviceDisplayName} skipped for this test')
            return CaseReturnCode.SUCCESS
        (grabberHandle,) = KYFG_Open(device_index_for_thread)
        print(f'Start UpdateCameraList for grabber {grabInfo.szDeviceDisplayName}')
        (status,camera_list) = KYFG_UpdateCameraList(grabberHandle)
        print(f'End UpdateCameraList for grabber {grabInfo.szDeviceDisplayName}')
        if len(camera_list) > 0:
            print(f'Found {len(camera_list)} cameras on grabber {grabInfo.szDeviceDisplayName}')
            (status,) = KYFG_Close(grabberHandle)
            return CaseReturnCode.SUCCESS
        elif len(camera_list) == 0:
            print(f'There are no cameras on grabber {grabInfo.szDeviceDisplayName}')
            (status,) = KYFG_Close(grabberHandle)
            return CaseReturnCode.NO_HW_FOUND

    if mainThread == 'True':
        for next_thread in background_threads:
            next_thread.join()
        print('\n\nRESULT OF TEST:')
        for key, value in threadsReturnCodes.items():
            print(key, 'Return Code: ', value)
        for v in threadsReturnCodes.values():
            assert v == 0, 'Something was wrong while test'
        return CaseReturnCode.SUCCESS


if __name__ == "__main__":
    try:
        args_ = ParseArgs()
        return_code = CaseRun(args_)
        print(f'Case return code: {return_code}')
    except Exception as ex:
        print(f"Exception of type {type(ex)} occurred: {str(ex)}")
        exit(-200)

    exit(return_code)
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
import subprocess
import platform
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
    parser.add_argument("--callbacks_maxcount", type=int, default=10000, help="Max Callback Count")
    parser.add_argument("--aux_wait_time_sec", type=int, default=30, help="Wait time for AUX")
    parser.add_argument("--stream_wait_time_sec", type=int, default=30, help="Stream Duration")
    return parser

def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)
gExe_file = None
def find_exe_in_folder(folder: pathlib.Path):
    global gExe_file
    if "linux" in platform.platform().lower() or 'tegra' in platform.platform().lower():
        gExe_file = folder.joinpath(pathlib.Path(__file__).name.replace(".py", ""))
        return
    for next_file in folder.iterdir():
        if next_file.is_dir():
            find_exe_in_folder(next_file)
        elif next_file.is_file() and next_file.name == pathlib.Path(__file__).name.replace(".py", ".exe"):
            gExe_file = next_file.as_posix()
            break

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
    global gExe_file
    callbacks_maxcount = args["callbacks_maxcount"]
    aux_wait_time_sec = args["aux_wait_time_sec"]
    stream_wait_time_sec = args["stream_wait_time_sec"]
    # case_folder = pathlib.Path.cwd().joinpath('binary_test_executables').joinpath(pathlib.Path(__file__).name.replace(".py", ""))
    case_folder = pathlib.Path(__file__).parent.parent.parent.joinpath('binary_test_executables').joinpath(pathlib.Path(__file__).name.replace(".py", ""))

    find_exe_in_folder(case_folder)
    print(gExe_file)
    assert gExe_file is not None, "Case file not found"
    if type(gExe_file) == pathlib.Path:
        gExe_file = gExe_file.as_posix()
    command = [gExe_file, "--device_index", str(device_index), "--callbacks_maxcount", str(callbacks_maxcount),
               "--aux_wait_time_sec", str(aux_wait_time_sec), "--stream_wait_time_sec", str(stream_wait_time_sec)]
    print(" ".join(command))
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    output, error = process.communicate(timeout=stream_wait_time_sec+aux_wait_time_sec+180)
    return_code = process.returncode
    print(output)
    print(error)
    assert return_code == 0 == len(error), "Test not passed"
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

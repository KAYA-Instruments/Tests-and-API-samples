# Common KAYA imports DO NOT EDIT!!!
import sys
import os
import argparse
sys.path.insert(0, os.environ['KAYA_VISION_POINT_PYTHON_PATH'])
from KYFGLib import *

# Common Case imports DO NOT EDIT!!!
from enum import IntEnum  # for CaseReturnCode

# additional imports required by particular case, ADD CASE SPECIFIC IMPORTS UNDER THIS LINE:
import pathlib
import subprocess


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
gExeFile = None
def find_exe(directory: pathlib.Path):
    global gExeFile
    for next_file in directory.iterdir():
        if next_file.name.endswith('.exe'):
            gExeFile = next_file
        elif next_file.is_dir() and next_file.name != 'obj':
            exe_file = find_exe(next_file)
def create_bat_file(bat_file: pathlib.Path, exe_file):
    with open(bat_file, 'w')as f: f.write(f'@echo off\n{exe_file} < input.txt')
def create_input_txt(input_file: pathlib.Path, *args):
    with open (input_file, 'a') as f:
        for arg in args:
            f.write(f"{str(arg)}\n")
        f.close()
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
    global gExeFile
    current_directory = pathlib.Path.cwd()
    root_directory = current_directory.joinpath('binary_test_executables').joinpath('case_3237')
    find_exe(root_directory)
    if gExeFile == None:
        print('There is no exe file')
        return CaseReturnCode.NO_HW_FOUND
    bat_file = gExeFile.parent.joinpath('start_case.bat')
    create_bat_file(bat_file, gExeFile.name)
    input_file = gExeFile.parent.joinpath('input.txt')
    if input_file.exists(): input_file.unlink()
    print(input_file)
    create_input_txt(input_file, r'\n')
    work_directory = gExeFile.parent.as_posix()
    bat_file = bat_file.as_posix()
    print('exe_file = ', gExeFile)
    print('bat_file = ', bat_file)
    print('input_file = ', input_file)
    process = subprocess.Popen(bat_file,
                               shell=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               text=True,
                               cwd=work_directory)
    stdout, stderr = process.communicate()
    print(stdout, stderr)
    assert "ERROR" not in stdout and len(stderr) == 0, print('Some errors while test')
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

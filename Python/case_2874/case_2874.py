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
def find_bat(directory: pathlib.Path):
    bat_file = None
    for next_file in directory.iterdir():
        if next_file.name.endswith('.bat'):
            bat_file = next_file
        elif next_file.is_dir():
            bat_file = find_bat(next_file)
    return bat_file
def find_exe(directory: pathlib.Path):
    exe_file = None
    for next_file in directory.iterdir():
        if next_file.name.endswith('.exe'):
            exe_file = next_file
        elif next_file.is_dir():
            exe_file = find_exe(next_file)
    return exe_file
def create_input_txt(input_file: pathlib.Path):
    with open (input_file, 'a') as f:
        f.write(f"y\n")
        f.write(f"n\n")
        f.write(r"\n")
        f.write("\n")
        f.write(r"\n")
        f.close()
def create_bat_file(bat_file: pathlib.Path):
    with open(bat_file, 'w')as f: f.write(f'@echo off\nKYFGLib_multi_cam_t9.exe < input.txt')
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
    (status, device_info) = KY_DeviceInfo(device_index)
    if device_info.m_Protocol != KY_DEVICE_PROTOCOL.KY_DEVICE_PROTOCOL_CLHS:
        print('Test could not run on this grabber')
        return CaseReturnCode.COULD_NOT_RUN
    current_directory = pathlib.Path.cwd()
    root_directory = current_directory.joinpath('binary_test_executables').joinpath('case_2874')
    # Find exe file
    exe_file = find_exe(root_directory)
    bat_file = exe_file.parent.joinpath('start_case.bat')
    input_file = exe_file.parent.joinpath('input.txt')
    if exe_file == None:
        return CaseReturnCode.NO_HW_FOUND
    if not input_file.exists():
        create_input_txt(input_file)
    if not bat_file.exists():
        create_bat_file(bat_file)
    work_directory = exe_file.parent.as_posix()
    bat_file = bat_file.as_posix()
    print('exe_file = ', exe_file)
    print('bat_file = ', bat_file)
    print('input_file = ',input_file)
    process = subprocess.Popen(bat_file,
                               shell=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               text=True,
                               cwd=work_directory)
    stdout, stderr = process.communicate()
    print(stdout, stderr)
    assert "All threads all images done loop 10 of 10" in stdout and len(stderr) == 0, 'Test Failed'
    lines = stdout.strip().split('\n')
    for line in lines:
        if 'image failed' in line:
            assert "0 image failed" in line, 'there is errors while test'
    print('Test Passed')
    print(f'\nExiting from CaseRun({args}) with code 0...')
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
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
import platform
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
    parser.add_argument('--example', type=str, default='KYFGLib_Example', help='Name of example folder')
    parser.add_argument('--input_line', type=str, default='deviceIndex; d; duration: 15; q;',
                        help='user input')
    parser.add_argument('--mode', type=str, default='Debug', help='Release or Debug')
    return parser

def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)
gExeFile = pathlib.Path()
def find_exe(directory: pathlib.Path, sample_name, mode):
    global gExeFile
    for next_file in directory.iterdir():
        if (next_file.name == f"{sample_name}.exe" or next_file.name == sample_name) and next_file.is_file():
            gExeFile = next_file
        elif next_file.is_dir() and next_file.name != "obj" \
             and f"{'Release' if mode == 'Debug' else 'Debug'}" not in next_file.name:
            find_exe(next_file, sample_name, mode)

def read_output(stdout):
    for line in stdout:
        print(line.decode('utf-8').strip())

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
    example = args['example']
    input_line = args['input_line']
    mode = args['mode']
    assert mode == 'Release' or mode == 'Debug', 'Unknown mode'
    variable_name = "KAYA_VISION_POINT_SAMPLE_API"
    variable_value = os.environ.get(variable_name)
    variable_path = pathlib.Path(variable_value)
    input_list = input_line.split('; ')
    index_of_duration = None
    duration = 0
    for next_item in range(len(input_list)):
        if "deviceIndex" in input_list[next_item]:
            input_list[next_item] = str(device_index)
        if "duration" in input_list[next_item]:
            index_of_duration = next_item
        item_list = input_list[next_item].split(': ')
        input_list[next_item] = item_list[-1]
    if index_of_duration is not None:
        duration_item = input_list.pop(index_of_duration)
        duration = int(duration_item.split(': ')[-1])
    find_exe(variable_path, example, mode)
    if gExeFile == pathlib.Path():
        print('Exe file not found')
        return CaseReturnCode.NO_HW_FOUND
    print(input_list)
    print("gExeFile", gExeFile)
    print('duration = ', duration)
    # exe_file = gExeFile.as_posix()
    exe_file = gExeFile
    print(exe_file)
    if 'Windows' in platform.platform():
        process = subprocess.Popen([exe_file.as_posix()], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
    else:
        process = subprocess.Popen([f'./{exe_file}'], stdin=subprocess.PIPE, cwd=exe_file, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
    print('pid = ', process.pid)
    delay = 10
    for command in input_list:
        current_command_index = input_list.index(command)
        if current_command_index == index_of_duration:
            print("Stream duration: ", duration)
            time.sleep(duration)
        else:
            time.sleep(delay)

        print(command)

        process.stdin.write(command.encode('utf-8') + b'\n')
        process.stdin.flush()
    try:
        process.stdin.close()
    except:
        print('stdin close error')
    print(process.stdout.read().decode('utf-8').strip())
    print(process.stderr.read().decode('utf-8').strip())
    # (stdout, stderr) = process.communicate()
    time.sleep(100)
    process.kill()
    # print(stdout, stderr)
    print('return Code = ', process.returncode)
    assert process.returncode == 0, 'Test not Passed'


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

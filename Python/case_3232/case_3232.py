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
import shlex
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
    parser.add_argument('--Width', type=int, default=512, help='New Width value')
    parser.add_argument('--Height', type=int, default=512, help='New Height value')
    parser.add_argument('--mode', type=str, default='Release', help='Release or debug')
    return parser


def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)


##########
# Definition
##########
gExeFile = pathlib.Path()


##########
# Functions
##########
def find_bat(directory: pathlib.Path):
    bat_file = None
    for next_file in directory.iterdir():
        if next_file.name.endswith('.bat'):
            bat_file = next_file
        elif next_file.is_dir():
            bat_file = find_bat(next_file)
    return bat_file


def find_exe(directory: pathlib.Path, sample_name, mode):
    global gExeFile
    for next_file in directory.iterdir():
        if (next_file.name == f"{sample_name}.exe" or next_file.name == sample_name) and next_file.is_file():
            gExeFile = next_file
        elif next_file.is_dir() and next_file.name != "obj" \
                and f"{'Release' if mode == 'Debug' else 'Debug'}" not in next_file.name:
            find_exe(next_file, sample_name, mode)


def change_camera_parameters_file(Width, Height, camera_params_file):
    with camera_params_file.open('r', errors="ignore") as cpf:
        file_data = cpf.readlines()
    for index, line in enumerate(file_data):
        if "Width:Integer:" in line:
            file_data[index] = f"Width:Integer:{Width}\n"
        elif "Height:Integer:" in line:
            file_data[index] = f"Height:Integer:{Height}\n"
    with camera_params_file.open('w', errors="ignore") as cpf:
        cpf.writelines(file_data)


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
    Width = args['Width']
    Height = args['Height']
    mode = args['mode']
    example_folder_name = "ParamsDumpAndLoad"
    example = "KYFGLib_ParamsDumpAndLoad"
    assert mode == 'Release' or mode == 'Debug', 'Unknown mode'

    source_folder = pathlib.Path.cwd().joinpath('_Tests')
    # source_folder = pathlib.Path.cwd().parent.parent.joinpath('_Tests')  # for current file running
    input_list = [f'{device_index}', "c", "d", "l", "e", "q"]
    example_work_directory = source_folder.joinpath(example_folder_name)
    find_exe(example_work_directory, example, mode)
    if gExeFile == pathlib.Path():
        print('Exe file not found')
        return CaseReturnCode.NO_HW_FOUND
    print('exe_file = ', gExeFile)
    if 'Windows' in platform.platform():
        process = subprocess.Popen([gExeFile.as_posix()], cwd=example_work_directory,
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    else:
        process = subprocess.Popen([f'./{gExeFile}'], stdin=subprocess.PIPE, cwd=example_work_directory,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
    print('pid = ', process.pid)
    delay = 10
    for command in input_list:

        print(command)
        time.sleep(delay)
        if command == 'l':
            change_camera_parameters_file(Width, Height, example_work_directory.joinpath('CameraParameters.txt'))

        process.stdin.write(command.encode('utf-8') + b'\n')
        try:
            process.stdin.flush()
        except:
            print('flush() error')
    try:
        process.stdin.close()
    except:
        print('stdin close error')
    print(process.stdout.read().decode('utf-8').strip())
    print(process.stderr.read().decode('utf-8').strip())
    # (stdout, stderr) = process.communicate()
    process.wait()
    # print(stdout, stderr)
    print('return Code = ', process.returncode)

    (grabberHandle,) = KYFG_Open(device_index)
    (status, cameraList) = KYFG_UpdateCameraList(grabberHandle)
    cameraHandle = cameraList[0]
    (status,) = KYFG_CameraOpen2(cameraHandle, None)
    (status, current_width) = KYFG_GetCameraValueInt(cameraHandle, "Width")
    (status, current_height) = KYFG_GetCameraValueInt(cameraHandle, "Height")
    print('current_width = ', current_width)
    print('current_height = ', current_height)
    (status,) = KYFG_CameraClose(cameraHandle)
    (status,) = KYFG_Close(grabberHandle)
    assert Height == current_height and current_width == Width, \
        'Test not passed. Expected parameters != got parameters'
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

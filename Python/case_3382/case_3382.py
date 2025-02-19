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


##########
# Definition
##########
build_Report = {}


##########
# Functions
##########
def findMSBuild():
    # Find VsDevCmd.bat file
    commands = ["cd/", "dir VsDevCmd.bat /s", ]
    find_cmd_line = subprocess.run('&&'.join(commands), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True,
                                   text=True)
    stdout_output = find_cmd_line.stdout.strip().split('\n')
    stderr_output = find_cmd_line.stderr.strip()
    stdout_output = stdout_output
    paths_to_cmd = []
    path_to_VsDevCmd = str
    for i in stdout_output:
        if 'Directory of ' in i:
            new_path = i.replace('Directory of ', '')
            paths_to_cmd.append(new_path.strip())
    for i in paths_to_cmd:
        if 'Microsoft Visual Studio' in i and '2017' in i:
            path_to_VsDevCmd = i + r'\VsDevCmd.bat'
    # Find MSBuild
    command_for_find_MSBuild = f'"{path_to_VsDevCmd}" && where MSBuild'
    start_searching_toMSBuild = subprocess.run(command_for_find_MSBuild, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                               shell=True, text=True)
    searching_output = start_searching_toMSBuild.stdout.strip().split('\n')
    path_to_MSBuild = None
    for i in searching_output:
        if 'Microsoft Visual Studio' in i and '2017' in i:
            path_to_MSBuild = i
    print('Path to MSBuild: ', path_to_MSBuild)
    return path_to_MSBuild


def build_for_windows(msbuild_file, file_path, platform):
    global build_Report
    print()
    print('*' * 30, file_path.name, '*' * 30)
    print()
    print('*' * 30, 'DEBUG BUILDING', '*' * 30)
    print()
    DebugLogfile = fr"{pathlib.Path(file_path).parent}\DebugBuildLogFile.log"
    ReleaseLogfile = fr"{pathlib.Path(file_path).parent}\ReleaseBuildLogFile.log"
    command = f'"{msbuild_file}" "{file_path}" /p:configuration=Debug /p:platform={platform} /flp:logfile="{DebugLogfile}"'
    print(command)
    p = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        close_fds=True
    )
    output, errors = p.communicate()
    outputLines = output.decode().strip().split('\n')
    print(output.decode())
    print('*' * 30, 'Release BUILDING', '*' * 30)
    logfile = fr"{pathlib.Path(file_path).parent}\BuildLogFile.log"
    command = f'"{msbuild_file}" "{file_path}" /p:configuration=Release /p:platform={platform} /flp:logfile="{ReleaseLogfile}"'
    print(command)
    p = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        close_fds=True
    )
    output, errors = p.communicate()
    releaseOutputLines = output.decode().strip().split('\n')
    print(output.decode())
    success_build = True
    for nextLine in outputLines:
        if 'Error(s)' in nextLine:
            if ' 0 Error(s)' not in nextLine:
                print('Errors and warnings that occurred during the build DEBUG process\nLook at the output')
                success_build = False
    for nextLine in releaseOutputLines:
        if 'Error(s)' in nextLine:
            if ' 0 Error(s)' not in nextLine:
                print('Errors and warnings that occurred during the build RELEASE process\nLook at the output')
                success_build = False
    build_Report[file_path.name] = success_build
    return success_build


def build_for_linux(file_path):
    global build_Report
    print()
    print('*' * 30, file_path.name, '*' * 30)
    print()
    print('*' * 30, 'LINUX BUILDING', '*' * 30)
    print()
    cmd = 'make'
    p = subprocess.run(
        cmd,
        cwd=file_path.parent,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
        close_fds=True
    )
    print(p.stdout, p.stderr, sep='\n')
    success_build = False
    if file_path.parent.joinpath(file_path.parent.name).exists():
        success_build = True
    else:
        print(f"{file_path.parent.joinpath(file_path.parent.name)} Doesn't exist")
    build_Report[file_path.name] = success_build
    return success_build


def iter_folder(folder: pathlib.Path, msbuild, vs_platform):
    system_platform = platform.system().lower()
    global build_Report
    for file in pathlib.Path.iterdir(folder):
        if pathlib.Path(file).is_dir():
            iter_folder(file, msbuild, vs_platform)
        else:
            if (file.name.endswith('.vcxproj') or file.name.endswith('.csproj')) and system_platform == 'windows':
                try:
                    build_for_windows(msbuild, file, vs_platform)
                except:
                    build_Report[file.name] = False
            elif file.name.startswith('Makefile') and system_platform == 'linux':
                try:
                    build_for_linux(file)
                except:
                    build_Report[file.name] = False



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
    global build_Report
    parent_path = pathlib.Path.cwd().joinpath('_Tests')
    # parent_path = pathlib.Path.cwd().parent.parent.joinpath('_Tests')  # for current folder running
    system_platform = platform.system().lower()
    if system_platform == 'windows':
        msbuild = findMSBuild()
    else:
        msbuild = None
    vs_platform = "x64" if is_python_64bit() else "win32"
    for file in pathlib.Path.iterdir(parent_path):
        if file.is_dir():
            iter_folder(file, msbuild, vs_platform)
    max_name_length = max(len(name) for name in build_Report.keys())  # Find max len for alignment
    for name, val in build_Report.items():
        formatted_name = name.ljust(max_name_length)
        print(f"{formatted_name} {val}")
    for val in build_Report.values():
        assert val is True, 'Not all of files built successful, check report'

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

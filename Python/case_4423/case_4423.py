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
    print('Path to MSBuild: ',path_to_MSBuild)
    return path_to_MSBuild
def build_for_windows(msbuild_file, file_path,platform):
    print('*' * 30, 'Release BUILDING', '*' * 30)
    logfile = fr"{pathlib.Path(file_path).parent}\BuildLogFile.log"
    command = f'"{msbuild_file}" "{file_path}" /p:configuration=Release /p:platform={platform} /t:Rebuild'
    print(command)
    p = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        close_fds=True
    )
    output, errors = p.communicate()
    releaseOutputLines = output.decode().strip()
    if errors:
        releaseErrorsLines = errors.decode().strip()
        print(releaseOutputLines, releaseErrorsLines, sep='\n')
    else:
        print(releaseOutputLines)
    for nextLine in releaseOutputLines:
        if 'Error(s)' in nextLine:
            assert ' 0 Error(s)' in nextLine,\
                'Errors and warnings that occurred during the build RELEASE process\nLook at the output'
def startCase(**kwargs):
    command = f"{gExeFile}"
    for k, v in kwargs.items():
        command += f" --{k} {v}"
    print("Start command", command)
    p = subprocess.Popen(command,shell=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               text=True)
    stdout, stderr = p.communicate()
    full_output = stdout
    if stderr is not None:
        full_output+=stderr
    print(full_output)
    return p.returncode

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
    (status, currentDeviceInfo) = KY_DeviceInfo(device_index)
    if currentDeviceInfo.m_Protocol != KY_DEVICE_PROTOCOL.KY_DEVICE_PROTOCOL_CoaXPress:
        return CaseReturnCode.NO_HW_FOUND
    current_directory = pathlib.Path.cwd()
    root_directory = current_directory.joinpath('binary_test_executables').joinpath('case_4423')
    projectFile = root_directory.joinpath("Case_4423/Case_4423.csproj").absolute().as_posix()
    msbuildFile = findMSBuild()
    assert msbuildFile is not None, "MSBuild not found"
    build_for_windows(msbuildFile, projectFile, "x64")
    find_exe(root_directory)
    assert gExeFile is not None, 'Build failure'
    return_code = startCase(unattended=1, deviceIndex=device_index)
    assert return_code==0
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

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
import shutil
import tarfile


def CaseArgumentParser():
    parser = argparse.ArgumentParser()
    # Common arguments for all cases DO NOT EDIT!!!
    parser.add_argument('--unattended', default=True, action='store_true', help='Do not interact with user')
    parser.add_argument('--no-unattended', dest='unattended', action='store_false')
    parser.add_argument('--deviceList', default=False, action='store_true',
                        help='Print list of available devices and exit')
    parser.add_argument('--deviceIndex', type=int, default=-1,
                        help='Index of PCI device to use, '
                             'run this script with "--deviceList" to see available devices and exit')
    # Other arguments needed for this specific case, PARSE CASE SPECIFIC ARGUMENTS UNDER THIS LINE:
    parser.add_argument("--vp_ver", default='VP1', type=str, help="Vision Point version")
    parser.add_argument("--trunk", default=True, action='store_true', help="Is trunk version")
    parser.add_argument("--branch", default=False, action='store_true', help="Is branch version")
    parser.add_argument("--targetVersion", default="", type=str, help="If branch is enable")
    parser.add_argument("--revision", default="10201", type=str, help="Number of revision")
    parser.add_argument("--file", default="", type=str, help="Setup file")
    return parser


def find_setup_file(VP_version, isTrunk, targetVersion, revision):
    path_base = pathlib.Path(r"/run/user/1000/gvfs/smb-share:server=kayawin10srv1,share=jenkins_last_builds/SW")
    folderPath = path_base.joinpath(VP_version).joinpath(f"{'trunk'}" if isTrunk else "branches")
    if targetVersion:
        folderPath.joinpath(targetVersion)
    for nextFile in folderPath.iterdir():
        if "Ubuntu" in platform.version() and "20." in platform.version():
            if f".{revision}_" in nextFile.name and f"Ubuntu_20" in nextFile.name:
                return nextFile.as_posix()
        if "Ubuntu" in platform.version() and "22." in platform.version():
            if f".{revision}_" in nextFile.name and f"Ubuntu_22" in nextFile.name:
                return nextFile.as_posix()
    return ""
def extract_tar_gz(tar_gz_path:pathlib.Path, extract_to_dir:pathlib.Path):
    if extract_to_dir.joinpath(tar_gz_path.name).exists():
        shutil.rmtree(extract_to_dir.joinpath(tar_gz_path.name.replace(".tar.gz", "")))
    with tarfile.open(tar_gz_path, "r:gz") as tar:
        tar.extractall(path=extract_to_dir)
def start_install(packageFolder: str):
    command = "echo Sar12345 | sudo -S sh install.sh -s"

    process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE,
                               cwd=packageFolder, shell=True)
    stdout, stderr = process.communicate()
    print(stdout)
    print(stderr)
    return process.returncode

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
    # (status, infosize_test) = KY_DeviceScan()
    # for x in range(0, infosize_test):
    #     (status, device_infos[x]) = KY_DeviceInfo(x)
    #     dev_info = device_infos[x]
        # print(f'Found device [{x}]: "{dev_info.szDeviceDisplayName}"' )

    # If only print of available devices list was requested
    if args["deviceList"]:
        return CaseReturnCode.SUCCESS  # we are done

    # deviceIndex == -1 means we need to ask user
    # if device_index < 0:
    #     # Ask user what device to use for this test
    #     # in unattended mode, use the first device detected in the system (index 0)
    #     if unattended:
    #         device_index = 0
    #         print(f'\n!!! deviceIndex {device_index} forcibly selected in unattended mode !!!')
    #     else:
    #         device_index = int(input(f'Select PCI device to use (0 ... {infosize_test - 1})'))
    #         print(f'\ndeviceIndex {device_index} selected')

    # Verify deviceIndex being in the allowed range
    # if device_index >= infosize_test:
    #     print(f'\nDevice with the index {device_index} does not exist, exiting...')
    #     return CaseReturnCode.NO_HW_FOUND

    # End of common KAYA prolog for "def CaseRun(args)"

    args = ParseArgs()
    vp_version = args["vp_ver"]
    trunk = args["trunk"]
    branch = args["branch"]
    revision = args["revision"]
    targetVersion = args["targetVersion"]
    setup_file = args["file"]
    if len(setup_file) == 0:
        setup_file = find_setup_file(vp_version, trunk, targetVersion, revision)
        assert len(setup_file) > 0, "Setup file not found"
    setup_file = pathlib.Path(setup_file)
    if pathlib.Path.cwd().joinpath(setup_file.name).exists():
        pathlib.Path.cwd().joinpath(setup_file.name).unlink()
    shutil.copy(setup_file, pathlib.Path.cwd().as_posix())
    extract_tar_gz(setup_file, pathlib.Path.cwd())
    return_code = start_install(
        pathlib.Path.cwd().joinpath(setup_file.name.replace(".tar.gz", "")).as_posix())
    assert return_code == 0, "Installation failed"

    print(f'\nExiting from CaseRun({args}) with code SUCCESS...')
    return CaseReturnCode.SUCCESS

def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)


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

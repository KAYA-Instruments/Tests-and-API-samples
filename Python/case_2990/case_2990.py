# Common KAYA imports DO NOT EDIT!!!
import sys
import os
import argparse
sys.path.insert(0, os.environ['KAYA_VISION_POINT_PYTHON_PATH'])
from KYFGLib import *

# Common Case imports DO NOT EDIT!!!
from enum import IntEnum  # for CaseReturnCode

# additional imports required by particular case, ADD CASE SPECIFIC IMPORTS UNDER THIS LINE:
import platform
import shutil

camHandleArray = {}


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
    parser.add_argument('--emb_json_incorrect', type=str, default='incorrect_KYHWLib_0x410_emb.json',
                        help='Path to incorrect JSON file')
    parser.add_argument('--emb_json_correct', type=str, default='KYHWLib_0x410_emb.json',
                        help='Path to correct JSON file')

    return parser

def check_log(path, string_to_check):
    log_file = None
    for file_name in os.listdir(path):
        if os.path.isfile(os.path.join(path, file_name)) and file_name.startswith("KAYA_python") and file_name.endswith(".log"):
            log_file = os.path.join(path, file_name)
            with open(log_file, "r", encoding="utf-8", errors='ignore') as log:
                lines = [line.rstrip() for line in log]
                data = "\n".join(lines)
                if string_to_check in data:
                    return True

    return False


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

    emb_json_incorrect = args.get('emb_json_incorrect')
    emb_json_correct = args.get('emb_json_correct')

    system_platform = platform.system().lower()
    current_folder_path = os.path.dirname(__file__)
    if system_platform == 'linux':
        JSON_FILE_PATH = os.environ['KAYA_VISION_POINT_LIB_PATH']
        LOG_FILE_PATH = os.environ['KAYA_VISION_POINT_LOGS']
    elif system_platform == 'windows':        
        JSON_FILE_PATH = os.environ['KAYA_VISION_POINT_BIN_PATH']
        LOG_FILE_PATH = os.environ['KAYA_VISION_POINT_LOGS']
    
    print("correct JSON: ", emb_json_correct)
    shutil.copy(os.path.join(os.path.dirname(__file__), emb_json_correct), JSON_FILE_PATH)

    (grabberHandle,) = KYFG_Open(device_index)
    KYFG_Close(grabberHandle)
    
    result = check_log(LOG_FILE_PATH, 'HW_INVALID_JSON_FILE')
    assert result == False, 'HW_INVALID_JSON_FILE is found in logs'
    
    
    print("incorrect JSON: ", emb_json_incorrect)
    shutil.copy(os.path.join(os.path.dirname(__file__), emb_json_incorrect), os.path.join(JSON_FILE_PATH, emb_json_incorrect.replace('incorrect_', '')))

    (grabberHandle,) = KYFG_Open(device_index)
    KYFG_Close(grabberHandle)
    
    result = check_log(LOG_FILE_PATH, 'HW_INVALID_JSON_FILE')
    assert result == True, 'HW_INVALID_JSON_FILE not found'

    print('JSON_FILE_PATH', JSON_FILE_PATH)
    os.remove(os.path.join(JSON_FILE_PATH,emb_json_correct))
    # replace incorrect JSON file with correct
    # shutil.copy(os.path.join(os.path.dirname(__file__), emb_json_correct), JSON_FILE_PATH)

    print(f'\nExiting from CaseRun({args}) with code 0...')
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
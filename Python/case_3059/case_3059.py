# Common KAYA imports DO NOT EDIT!!!
import sys
import os
import argparse
sys.path.insert(0, os.environ['KAYA_VISION_POINT_PYTHON_PATH'])
from KYFGLib import *

# Common Case imports DO NOT EDIT!!!
from enum import IntEnum  # for CaseReturnCode

# additional imports required by particular case, ADD CASE SPECIFIC IMPORTS UNDER THIS LINE:
import json
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
    parser.add_argument('--fileName', type=str, default='VPProject.fgprj', help='Path to project file')

    return parser

def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)


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
    # scan and open camera
    project_file=pathlib.Path(__file__).parent.joinpath(args['fileName'])
    assert project_file.exists(), 'Project file not found'
    project_file=str(project_file)
    (device_handle,)=KYFG_OpenEx(device_index,project_file)
    # (device_handle,) = KYFG_Open(device_index)
    device_info = device_infos[device_index]
    (status, camHandleArray_col) = KYFG_UpdateCameraList(device_handle)
    print(f'Camera scan result:\nStatus: {status}\nCamHandleArray: {camHandleArray_col}')

    with open (project_file, 'r') as pf:
        prjson=json.load(pf)
    grabber_parameters=prjson['Parameters']['Grabber']
    cameras = prjson['Parameters']['Cameras']
    #checking for grabber parameters
    print('Checking for grabber parameters')
    for i in grabber_parameters:
        for param_name,param_value in i.items():

            try:
                (status, value) = KYFG_GetGrabberValue(device_handle, param_name)
            except:
                (status, ind, value) = KYFG_GetGrabberValue(device_handle, param_name)
            assert param_value["value"]==value,f'''The project was saved incorrectly for grabber: parameter: {param_name}
                                    Saved value: {param_value["value"]}
                                    received value: {value}'''

            print(f'Grabber parameter {param_name}: {param_value["value"]} was correctly saved')
    #checking for camera parametrs
    print('Checking for camera parametrs')
    for index, param_list in cameras.items():
        if type(param_list)==list:
            camHandle=camHandleArray_col[int(index)]
            (status) = KYFG_CameraOpen2(camHandleArray_col[int(index)], None)
            for parameter in param_list:
                for x,y in parameter.items():
                    if type(y)==dict:
                        try:(status, getted_value) = KYFG_GetCameraValue(camHandle, x)
                        except: (status, ind, getted_value) = KYFG_GetCameraValue(camHandle, x)
                        print(status, ind, getted_value)
                        assert str(getted_value) == str(y["value"]) or str(ind) == str(y["value"]), f'''The project was saved incorrectly for camera: parameter: {x}
                                                                    Saved value: {y["value"]}
                                                                    received value: {getted_value}'''
                        print(f'Camera parameter {x}: {y["value"]} was correctly saved')
            (status,)=KYFG_CameraClose(camHandleArray_col[int(index)])



    (status,) = KYFG_Close(device_handle)
    print(f'\nExiting from CaseRun({args}) with code 0...')
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

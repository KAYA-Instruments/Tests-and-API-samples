# Common KAYA imports DO NOT EDIT!!!
import sys
import os
import argparse
sys.path.insert(0, os.environ['KAYA_VISION_POINT_PYTHON_PATH'])
from KYFGLib import *

# Common Case imports DO NOT EDIT!!!
from enum import IntEnum  # for CaseReturnCode

# additional imports required by particular case, ADD CASE SPECIFIC IMPORTS UNDER THIS LINE:
# For example:
# import numpy as np
# import cv2
# from numpngw import write_png
# grabber_handle = 0
###################### Defines ####################################
def system_initialization(device_index):
    # global grabber_handle
    (grabber_handle,) = KYFG_Open(device_index)
    (CameraScan_status, camHandleArray) = KYFG_UpdateCameraList(grabber_handle)
    assert len(camHandleArray)!=0, 'Thera is no cameras on this grabber'
    camHandlerChameleon = -102;
    if (len(camHandleArray) == 0):
        print("No cameras found ...")
        return camHandlerChameleon
    for camHandle in camHandleArray:
        (Status, camInfo) = KYFG_CameraInfo2(camHandle)
        print("version: ", str(camInfo.version))
        cameraName = camInfo.deviceModelName
        if "Chameleon" in cameraName:
            camHandlerChameleon = camHandle
    return camHandlerChameleon, grabber_handle

def connectToGrabber(grabberIndex):
    (connected_fghandle,) = KYFG_Open(grabberIndex)
    (status, tested_dev_info) = KY_DeviceInfo(grabberIndex)
    print("Good connection to grabber " + str(grabberIndex) + ": " + tested_dev_info.szDeviceDisplayName + ", handle= " + str(connected_fghandle))
    return connected_fghandle

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
    parser.add_argument('--suffixFalse', type=str, default='', help='suffix for crach test')

    return parser

path = os.environ.get('KAYA_VISION_POINT_SAMPLE_DATA')

################################## Main #################################################################




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

    suffixFalse = args['suffixFalse']

    pass_count = 0
    fail_count = 0

    Chameleon_camera_handle, grabber_handle = system_initialization(device_index)
    if Chameleon_camera_handle == -102:
        print('There is no Chameleon on this grabber')
        return CaseReturnCode.NO_HW_FOUND


    print("Check override KAYA_Chameleon.xml")
    try:
        if platform.system() == "Windows":
            (KYFG_CameraOpen2_status,) = KYFG_CameraOpen2(Chameleon_camera_handle, path + "\\KAYA_Chameleon.xml" + suffixFalse)
        elif platform.system() == "Linux":
            (KYFG_CameraOpen2_status,) = KYFG_CameraOpen2(Chameleon_camera_handle, path + "//KAYA_Chameleon.xml" + suffixFalse)
    except:
        print(" Could not found xml file")
        fail_count += 1
        assert fail_count == 0

    try:
        (status, link_reset) = KYFG_GetCameraValueInt(Chameleon_camera_handle, "LinkReset")
    except KYException as err:
        print(err + " Could not found LinkReset feature")
        fail_count += 1
        assert fail_count == 0
    else:
        print("Success: found LinkReset feature")
        pass_count += 1

    try:
        (status, link_reset) = KYFG_GetCameraValueInt(Chameleon_camera_handle, "DeviceLinkID")
    except KYException as err:
        print(err + " Could not found DeviceLinkID feature")
        fail_count += 1
        assert fail_count == 0
    else:
        print("Success: found DeviceLinkID feature")
        pass_count += 1

    try:
        (status, link_reset) = KYFG_GetCameraValueInt(Chameleon_camera_handle, "MasterHostLinkID")
    except KYException as err:
        print(err + " Could not found MasterHostLinkID feature")
        fail_count += 1
        assert fail_count == 0
    else:
        print("Success: found MasterHostLinkID feature")
        pass_count += 1

    try:
        (status, link_reset) = KYFG_GetCameraValueEnum(Chameleon_camera_handle, "LinkConfig")
    except KYException as err:
        print(err + " Could not found LinkConfig feature")
        fail_count += 1
        assert fail_count == 0
    else:
        print("Success: found LinkConfig feature")
        pass_count += 1

    try:
        (status, link_reset) = KYFG_GetCameraValueEnum(Chameleon_camera_handle, "LinkConfigDefault")
    except KYException as err:
        print(err + " Could not found LinkConfigDefault feature")
        fail_count += 1
        assert fail_count == 0
    else:
        print("Success: found LinkConfigDefault feature")
        pass_count += 1

    (CameraClose_status,) =KYFG_CameraClose(Chameleon_camera_handle)

    print("\nCheck override KAYA_Chameleon_CXP1.1.xml\n")
    if platform.system() == "Windows":
        (KYFG_CameraOpen2_status,) = KYFG_CameraOpen2(Chameleon_camera_handle, path + "\\KAYA_Chameleon_CXP1.1.xml")
    elif platform.system() == "Linux":
        (KYFG_CameraOpen2_status,) = KYFG_CameraOpen2(Chameleon_camera_handle, path + "//KAYA_Chameleon_CXP1.1.xml")

    try:
        (status, link_reset) = KYFG_GetCameraValueInt(Chameleon_camera_handle, "LinkReset")
    except KYException as err:
        print("Success: not found LinkReset feature")
        pass_count += 1
    else:
        print(err + " Found LinkReset feature")
        fail_count += 1
        assert fail_count == 0

    try:
        (status, link_reset) = KYFG_GetCameraValueInt(Chameleon_camera_handle, "DeviceLinkID")
    except KYException as err:
        print("Success: not found DeviceLinkID feature")
        pass_count += 1
    else:
        print(err + " Found DeviceLinkID feature")
        fail_count += 1
        assert fail_count == 0

    try:
        (status, link_reset) = KYFG_GetCameraValueInt(Chameleon_camera_handle, "MasterHostLinkID")
    except KYException as err:
        print("Success: not found MasterHostLinkID feature")
        pass_count += 1
    else:
        print(err + " Found MasterHostLinkID feature")
        fail_count += 1
        assert fail_count == 0

    try:
        (status, link_reset) = KYFG_GetCameraValueEnum(Chameleon_camera_handle, "LinkConfig")
    except KYException as err:
        print("Success: not found LinkConfig feature")
        pass_count += 1
    else:
        print(err + " Found LinkConfig feature")
        fail_count += 1
        assert fail_count == 0

    try:
        (status, link_reset) = KYFG_GetCameraValueEnum(Chameleon_camera_handle, "LinkConfigDefault")
    except KYException as err:
        print("Success: not found LinkConfigDefault feature")
        pass_count += 1
    else:
        print(err + " Found LinkConfigDefault feature")
        fail_count += 1
        assert fail_count == 0

    (CameraClose_status,) =KYFG_CameraClose(Chameleon_camera_handle)
    (Grabber_Close_status,) = KYFG_Close(grabber_handle)

    print("Passed: " + str(pass_count))
    print("Failed: " + str(fail_count))

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

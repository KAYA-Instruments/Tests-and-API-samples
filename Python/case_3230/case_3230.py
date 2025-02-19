# Common KAYA imports DO NOT EDIT!!!
import sys
import os
import argparse
sys.path.insert(0, os.environ['KAYA_VISION_POINT_PYTHON_PATH'])
from KYFGLib import *

# Common Case imports DO NOT EDIT!!!
from enum import IntEnum  # for CaseReturnCode

# additional imports required by particular case, ADD CASE SPECIFIC IMPORTS UNDER THIS LINE:
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
    parser.add_argument('--chameleonDeviceIndex', type=int, default=0,
                        help='Index of PCI device to use, '
                             'run this script with "--deviceList" to see available devices and exit')
    parser.add_argument('--camera', type=str, default='Chameleon',
                        help='Index of PCI device to use, '
                             'run this script with "--deviceList" to see available devices and exit')

    return parser

camHandleArray = {}


class DeviceEventCallbackStructure:
    event_recognized=False
    # def __init__(self) -> None:
    #     self.event_recognized = False


def Device_event_callback_func(handle, context):
    DeviceEventCallbackStructure.event_recognized=True


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

    camera_from_param = args['camera']
    chameleon_device_index = None

    for x in range(0, len(device_infos)):
        dev_info = device_infos[x]
        print(dev_info.szDeviceDisplayName.lower())

        if camera_from_param in dev_info.szDeviceDisplayName:
            print(True)
            chameleon_device_index = x

    if chameleon_device_index==None:
        print('No Chameleon found on your machine.')
        return CaseReturnCode.NO_HW_FOUND
    # Open frame grabber
    (chameleonGrabberHandle,) = KYFG_Open(chameleon_device_index)
    (CameraScan_status, camHandleArray[chameleon_device_index]) = KYFG_UpdateCameraList(chameleonGrabberHandle)
    KYFG_CameraOpen2(camHandleArray[chameleon_device_index][0], None)

    (grabberHandle,) = KYFG_Open(device_index)
    event_callback_structure = DeviceEventCallbackStructure()
    (KYDeviceEventCallBackRegister_status,) = KYDeviceEventCallBackRegister(grabberHandle,
                                                                            Device_event_callback_func,
                                                                            py_object(event_callback_structure))

    (CameraScan_status, camHandleArray[device_index]) = KYFG_UpdateCameraList(grabberHandle)
    cameras_length = len(camHandleArray[device_index])
    print("cameras_length", cameras_length)

    if cameras_length==0:
        print('Camera not found')
        return CaseReturnCode.NO_HW_FOUND

    for i in range(cameras_length):
        cameraHandle = camHandleArray[device_index][i]
        (Status, camInfo) = KYFG_CameraInfo2(cameraHandle)

        if camera_from_param in camInfo.deviceModelName:
            print(camInfo.deviceModelName, 'is open')
            DeviceEventCallbackStructure.event_recognized = False
            KYFG_CameraOpen2(cameraHandle, None)
            print("camera is opened")
            (kycs_status, pEvent) = KYCS_GenerateCxpEvent(chameleonGrabberHandle)
            print(pEvent)

            time.sleep(0.5)
            KYFG_CameraClose(cameraHandle)
            assert event_callback_structure.event_recognized, 'KYDEVICE_EVENT_CXP2_EVENT event doesn\'t recognize'
            print('KYDEVICE_EVENT_CXP2_EVENT event recognize')

    KYFG_Close(grabberHandle)
    KYFG_Close(chameleonGrabberHandle)

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
# Common KAYA imports DO NOT EDIT!!!
import sys
import os
import argparse
sys.path.insert(0, os.environ['KAYA_VISION_POINT_PYTHON_PATH'])
from KYFGLib import *

# Common Case imports DO NOT EDIT!!!
from enum import IntEnum  # for CaseReturnCode

# additional imports required by particular case, ADD CASE SPECIFIC IMPORTS UNDER THIS LINE:


###################### Defines ####################################
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
    parser.add_argument('--cameraModel', type=str,default='Iron2020eM', help='Camera model')
    return parser
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
    (status, device_info) = KY_DeviceInfo(device_index)
    if device_info.m_Protocol != KY_DEVICE_PROTOCOL.KY_DEVICE_PROTOCOL_CoaXPress:
        print('Test could not run on this grabber')
        return CaseReturnCode.COULD_NOT_RUN
    cameraModel=args['cameraModel']
    dev_info = device_infos[device_index]
    # if dev_info.m_Protocol != KY_DEVICE_PROTOCOL.KY_DEVICE_PROTOCOL_CoaXPress or dev_info.m_Flags != KY_DEVICE_INFO_FLAGS.GRABBER or dev_info.DeviceGeneration != 2:  # Check that the grabber protocol is CXP and it is not camera simulator
    #     print("Selected incorrect device fot the test!")
    #     return CaseReturnCode.NO_HW_FOUND

    (Grabber_handle,) = KYFG_Open(device_index)
    print(f"Good connection to device {str(device_index)} handle= {str(Grabber_handle)}")
    (CameraScan_status, camHandleArray) = KYFG_UpdateCameraList(Grabber_handle)

    cxp2_cameras_index = []
    print(camHandleArray)

    for x in range(len(camHandleArray)):
        camera_handle = camHandleArray[x]

        (KYFG_CameraOpen2_status,) = KYFG_CameraOpen2(camera_handle, None)
        (status, camera_info)=KYFG_CameraInfo2(camera_handle)
        print(camera_info.deviceModelName)
        if cameraModel not in camera_info.deviceModelName :
            (status,)=KYFG_CameraClose(camera_handle)
            continue
        (status, cxp_version_used) = KYFG_GetCameraValueEnum(camera_handle, "VersionsSupported_2_0")
        if cxp_version_used == True:
            cxp2_cameras_index.append(camera_handle)
        else:
            print(f"The camera {x} does not supports CoaXPress 2.0 ")
        (KYFG_CameraClose_status,) = KYFG_CameraClose(camera_handle)
    print(cxp2_cameras_index)
    if not cxp2_cameras_index:
        print("No cameras that supports CXP 2.0 found")
        KYFG_Close(Grabber_handle)
        return CaseReturnCode.NO_HW_FOUND
    print("Change CXP Version")
    for i in range(8):
        (status,)=KYFG_SetGrabberValueBool(Grabber_handle, f"CameraDiscoveryCxp2SuppressLink{i}", True)
        print(status)
    (CameraScan_status, camHandleArray) = KYFG_UpdateCameraList(Grabber_handle)
    for x in cxp2_cameras_index:
        print('CAMERA: ',x)
        camera_handle = x
        (KYFG_CameraOpen2_status,) = KYFG_CameraOpen2(camera_handle, None)
        (stataus, cxp_version_used) = KYFG_GetCameraValueEnum(camera_handle, "VersionUsed")
        assert cxp_version_used == 65537 or cxp_version_used == 65536
    for i in range(8):
        KYFG_SetGrabberValueBool(Grabber_handle, f"CameraDiscoveryCxp2SuppressLink{i}", False)
    KYFG_Close(Grabber_handle)
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
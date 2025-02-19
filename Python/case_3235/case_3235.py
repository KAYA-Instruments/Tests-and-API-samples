# Common KAYA imports DO NOT EDIT!!!
import sys
import os
import argparse
sys.path.insert(0, os.environ['KAYA_VISION_POINT_PYTHON_PATH'])
from KYFGLib import *

# Common Case imports DO NOT EDIT!!!
from enum import IntEnum  # for CaseReturnCode

# additional imports required by particular case, ADD CASE SPECIFIC IMPORTS UNDER THIS LINE:


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
    parser.add_argument('--number_of_tests', type=int, default=30, help='number of iteration for loop')
    parser.add_argument('--camera',type=str,default='CLHS', help='Camera name')
    return parser

def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)
############Callback function
class Stream_struct:
    def __init__(self):
        self.frames_acquired=0
        self.frames_dropped=0
        return
def callback_funk(buff_handle, user_context):

    user_context.frames_acquired+=1
    print(f'Frames acquired {user_context.frames_acquired}')







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
    if device_info.m_Protocol != KY_DEVICE_PROTOCOL.KY_DEVICE_PROTOCOL_CLHS:
        print('Test could not run on this grabber')
        return CaseReturnCode.COULD_NOT_RUN
    number_of_tests=args['number_of_tests']
    cameraName=args['camera']
    grabber_handle=0
    for i in range(infosize_test):
        (status, grabber_info) = KY_DeviceInfo(i)
        if cameraName in grabber_info.szDeviceDisplayName:
            (grabber_handle,) = KYFG_Open(i)
            print(f'Device {grabber_info.szDeviceDisplayName} is open')
        else:continue
    if grabber_handle ==0:
        print('There is no CLHS grabbers on this computer')
        return CaseReturnCode.NO_HW_FOUND
    (status,camera_list)=KYFG_UpdateCameraList(grabber_handle)
    assert len(camera_list)!=0, 'There is no cameras on this grabber'
    error_count = 0
    for camera_handle in camera_list:
        (status,camera_info)=KYFG_CameraInfo2(camera_handle)
        (status,)=KYFG_CameraOpen2(camera_handle, None)
        try:
            if KYFG_IsCameraValueImplemented(camera_handle, "TriggerMode"):
                KYFG_SetCameraValueEnum(camera_handle, "TriggerMode", 0)
        except:
            pass
        print(f'Camera {camera_info.deviceModelName} {camera_info.deviceVendorName} is open')
        (status,stream_handle)=KYFG_StreamCreateAndAlloc(camera_handle, 16,0)
        stream_struct=Stream_struct()
        (status,)=KYFG_StreamBufferCallbackRegister(stream_handle, callback_funk, stream_struct)
        print('Stream Started')
        for i in range(number_of_tests):
            (status,)=KYFG_CameraStart(camera_handle,stream_handle, 0)
            (status,)=KYFG_CameraStop(camera_handle)
        (status,stream_struct.frames_dropped)=KYFG_GetGrabberValueInt(grabber_handle, "DropFrameCounter")
        (status,)=KYFG_StreamBufferCallbackUnregister(stream_handle,callback_funk)
        (status,)=KYFG_StreamDelete(stream_handle)
        (status,)=KYFG_CameraClose(camera_handle)
        print(
            f'\nRESULTS\nFrames acqured: {stream_struct.frames_acquired}\nFrames dropped: {stream_struct.frames_dropped}')
        if stream_struct.frames_dropped != 0 :
            print(f'{stream_struct.frames_dropped} dropped during stream')
            error_count+=1
    (status,)=KYFG_Close(grabber_handle)
    assert error_count == 0, 'There are errors while test'


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

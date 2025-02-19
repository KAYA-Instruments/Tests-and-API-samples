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
import math


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
    parser.add_argument('--camera', type=str, default='Iron253C', help='Camera for test case')
    parser.add_argument('--width',type=int, default=1024,help='Width of the camera')
    parser.add_argument('--height', type=int, default=512, help='Height of the camera')
    parser.add_argument('--exposureTime', type=float, default=1000.0, help='Height of the camera')
    parser.add_argument('--triggerCount', type=int, default=300, help='Height of the camera')
    return parser

def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)
#########Callback func
class StramStruct:
    def __init__(self):
        self.frame_counter=0
        return
class TestStruct:
    def __init__(self):
        self.total_tests=0
        self.successful_tests=0
        return
def callback_func(buffHandle,userContext):
    userContext.frame_counter+=1
    print(f'Frames acquired {userContext.frame_counter}')

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
    camera=args['camera']
    width=args['width']
    height=args['height']
    exposureTime=args['exposureTime']
    trigger_count=args['triggerCount']
    test_struct=TestStruct()
    (grabberHandle,)=KYFG_Open(device_index)
    (status,cameraList)=KYFG_UpdateCameraList(grabberHandle)
    assert len(cameraList)!=0, 'There is no cameras on this device'
    camera_on_grabber=False
    for cameraHandle in cameraList:
        (status,camInfo)=KYFG_CameraInfo2(cameraHandle)
        if camera == camInfo.deviceModelName:
            camera_on_grabber=True
            break
    if camera_on_grabber==False:
        print (f'There is no camera {camera} on this grabber')
        return CaseReturnCode.NO_HW_FOUND
    for cameraHandle in cameraList:
        (status, camera_info) = KYFG_CameraInfo2(cameraHandle)
        if camera != camera_info.deviceModelName:
            continue
        (status,)=KYFG_CameraOpen2(cameraHandle,None)
        try:
            (status,)=KYFG_SetCameraValueEnum(cameraHandle, "TriggerMode", 0)
        except:
            (status,) = KYFG_CameraClose(cameraHandle)
            print(f'Trigger mode is not supported on camera {camera_info.deviceVendorName} {camera_info.deviceModelName}')
            continue
        print(f'Camera {camera_info.deviceModelName} {camera_info.deviceVendorName} is open')
        #Set camera value
        (status,) = KYFG_SetGrabberValueInt(grabberHandle, "CameraSelector", cameraList.index(cameraHandle))
        (status,)=KYFG_SetCameraValueInt(cameraHandle, "Width", width)
        (status,)=KYFG_SetCameraValueInt(cameraHandle, "Height", height)
        (status,max_fps)=KYFG_GetCameraValueFloat(cameraHandle, "AcquisitionFrameRateMax")
        frame_fps=max_fps*0.95
        (status,)=KYFG_SetCameraValueFloat(cameraHandle, "AcquisitionFrameRate", frame_fps)
        KYFG_SetCameraValueEnum(cameraHandle, "ExposureAuto", 0)
        (status,) = KYFG_SetCameraValueFloat(cameraHandle, "ExposureTime", exposureTime)
        if not KYFG_IsCameraValueImplemented(cameraHandle, "TriggerMode"):
            return CaseReturnCode.NO_HW_FOUND
        (status,) = KYFG_SetCameraValueEnum(cameraHandle, "TriggerMode", 1)
        frame_period_usec=1000000/frame_fps
        #Set grbber value
        # Set the TimerControl parameters to generate the trigger to the camera.

        (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "TimerSelector", "Timer0")
        (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "TimerTriggerSource", "KY_TIMER_ACTIVE_1")
        (status,) = KYFG_SetGrabberValueFloat(grabberHandle, "TimerDelay", frame_period_usec/2)
        (status,) = KYFG_SetGrabberValueFloat(grabberHandle, "TimerDuration",frame_period_usec/2)
        (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "TimerActivation", "LevelHigh")
        # Set the second trigger to run first trigger
        (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "TimerSelector", "Timer1")
        (status,)=KYFG_SetGrabberValueFloat(grabberHandle, "TimerDelay", 1.0)
        (status,) = KYFG_SetGrabberValueFloat(grabberHandle, "TimerDuration",frame_period_usec*trigger_count)
        (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "TimerActivation", "RisingEdge")
        (status,) = KYFG_SetGrabberValueEnum(grabberHandle, "TimerTriggerSource", 43) #Software
        # Enable the camera trigger
        (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "CameraTriggerSource", "KY_TIMER_ACTIVE_0")
        (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "CameraTriggerActivation", "AnyEdge")
        (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "CameraTriggerMode", "On")
        #stream create
        (status,streamHandle)=KYFG_StreamCreateAndAlloc(cameraHandle,16,0)
        stream_struct=StramStruct()


        duration = (frame_period_usec * trigger_count) / 1000000
        (status,)=KYFG_StreamBufferCallbackRegister(streamHandle,callback_func,stream_struct)
        (status,)=KYFG_CameraStart(cameraHandle,streamHandle,0)


        KYFG_GrabberExecuteCommand(grabberHandle, "TimerTriggerSoftware")
        time.sleep(duration)
        (status,)=KYFG_CameraStop(cameraHandle)
        (status,) = KYFG_StreamBufferCallbackUnregister(streamHandle,callback_func)
        (status,) = KYFG_StreamDelete(streamHandle)
        (status,frame_count) = KYFG_GetGrabberValueInt(grabberHandle, "RXFrameCounter")
        print('frame_count ',frame_count)
        print('trigger_count',trigger_count)

        (status,) = KYFG_CameraClose(cameraHandle)
        test_struct.total_tests+=1
        assert trigger_count <= frame_count, f'\nTest does not passed: \nFrame acquired:{frame_count}\nTriggers sent: {trigger_count}'
        test_struct.successful_tests+=1
    (status,) = KYFG_Close(grabberHandle)
    print(f'\nRESULTS\nTotal tests carried out: {test_struct.total_tests}\nSuccessful tests: {test_struct.successful_tests}')
    print(f'\nExiting from CaseRun({args}) with code 0...')

    return CaseReturnCode.SUCCESS
if __name__ == "__main__":
    # try:
        args_ = ParseArgs()
        return_code = CaseRun(args_)
        print(f'Case return code: {return_code}')
    # except Exception as ex:
    #     print(f"Exception of type {type(ex)} occurred: {str(ex)}")
    #     exit(-200)
    #
    # exit(return_code)

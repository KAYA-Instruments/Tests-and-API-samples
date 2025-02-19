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
import threading
import asyncio
caseStructDict= {}


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
    parser.add_argument('--test_time', type=int, default=10,help='Duration of test')
    parser.add_argument('--withMultiprocess',type=bool,default=True,help='With using multiprocess')
    return parser

def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)
async def async_interrupt(cameraHandle, grabberHandle,testTime):
    (status, camInfo) = KYFG_CameraInfo2(cameraHandle)
    print(f'Start thread for {camInfo.deviceModelName}')
    (status,)=KYFG_CameraOpen2(cameraHandle, None)
    try:
        (status, WidthMin) = KYFG_GetCameraValueInt(cameraHandle, "WidthMin")
        (status, HeightMin) = KYFG_GetCameraValueInt(cameraHandle, "HeightMin")
        (status,) = KYFG_SetCameraValueInt(cameraHandle, "Width", WidthMin)
        (status,) = KYFG_SetCameraValueInt(cameraHandle, "Height", HeightMin)
        (status, maxFps) = KYFG_GetCameraValueFloat(cameraHandle, "AcquisitionFrameRateMax")
        (status,) = KYFG_SetCameraValueFloat(cameraHandle, "AcquisitionFrameRate", maxFps)
    except:
        (status,) = KYFG_SetCameraValueInt(cameraHandle, "Width", 16)
        (status,) = KYFG_SetCameraValueInt(cameraHandle, "Height", 1)
        (status,) = KYFG_SetCameraValueFloat(cameraHandle, "AcquisitionFrameRate",100.0)
    (status,streamHandle) = KYFG_StreamCreateAndAlloc(cameraHandle,16,0)
    print('Stream start for camera', camInfo.deviceModelName)
    (status,) = KYFG_CameraStart(cameraHandle, streamHandle, 0)
    time.sleep(round(testTime/2))
    (status, camInfo) = KYFG_CameraInfo2(cameraHandle)
    try:
        (status, fps) = KYFG_GetCameraValueFloat(cameraHandle, "AcquisitionFrameRate")
        print('set AcquisitionFrameRate for', camInfo.deviceModelName)
        (status, Width) = KYFG_GetCameraValueInt(cameraHandle, "Width")
        print('set Width', camInfo.deviceModelName)
        (status, Height) = KYFG_GetCameraValueInt(cameraHandle, "Height")
        print('set Height', camInfo.deviceModelName)
        (status,) = KYFG_SetGrabberValueEnum(grabberHandle, "TriggerMode", 1)
        print('set TriggerMode', camInfo.deviceModelName)
        (status,) = KYFG_SetGrabberValueFloat(grabberHandle, "TimerDuration", 100000.0)
        print('set TimerDuration', camInfo.deviceModelName)
        (status,) = KYFG_SetGrabberValueFloat(grabberHandle, "TimerDelay", 100000.0)
        print('set TimerDelay', camInfo.deviceModelName)
        (status,) = KYFG_SetGrabberValueEnum(grabberHandle, "TimerTriggerSource", 2)
        print('set TimerTriggerSource', camInfo.deviceModelName)
        (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "TriggerEventMode", 'AnyEdge')
        print('set TriggerEventMode', camInfo.deviceModelName)
    except:
        print('Not all settings are set on the camera')
    time.sleep(round(testTime/2))
    print('Stream stop for camera', camInfo.deviceModelName)
    (status,) = KYFG_CameraStop(cameraHandle)
    (status,) = KYFG_StreamDelete(streamHandle)
    (status,) = KYFG_CameraClose(cameraHandle)
    print(f'Stop thread for {camInfo.deviceModelName}')
def run_async_function(cameraHandle, grabberHandle, testTime):
    asyncio.run(async_interrupt(cameraHandle,grabberHandle, testTime))

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

    # Other parameters used by this particular case
    testTime=args['test_time']
    (grabberHandle,) = KYFG_Open(device_index)
    multiProcess=args["withMultiprocess"]
    (status, cameraList) = KYFG_UpdateCameraList(grabberHandle)
    print(cameraList)
    print(len(cameraList), 'Cameras detected')
    assert (len(cameraList)) != 0, 'There are no cameras on this grabber'
    if multiProcess:
        threads = []
        for i in range(len(cameraList)):
            thread = threading.Thread(target=run_async_function, args=(cameraList[i],grabberHandle, testTime))
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()
    else:
        # Opening all cameras
        for cameraHandle in cameraList:
            (status, camInfo) = KYFG_CameraInfo2(cameraHandle)
            print(f'Start thread for {camInfo.deviceModelName}')
            (status,) = KYFG_CameraOpen2(cameraHandle, None)
            try:
                (status, WidthMin) = KYFG_GetCameraValueInt(cameraHandle, "WidthMin")
                (status, HeightMin) = KYFG_GetCameraValueInt(cameraHandle, "HeightMin")
                (status,) = KYFG_SetCameraValueInt(cameraHandle, "Width", WidthMin)
                (status,) = KYFG_SetCameraValueInt(cameraHandle, "Height", HeightMin)
                (status, maxFps) = KYFG_GetCameraValueFloat(cameraHandle, "AcquisitionFrameRateMax")
                (status,) = KYFG_SetCameraValueFloat(cameraHandle, "AcquisitionFrameRate", maxFps)
            except:
                (status,) = KYFG_SetCameraValueInt(cameraHandle, "Width", 16)
                (status,) = KYFG_SetCameraValueInt(cameraHandle, "Height", 1)
                (status,) = KYFG_SetCameraValueFloat(cameraHandle, "AcquisitionFrameRate", 100.0)
        # Start stream for all cameras
        streamHandleList=[]
        for cameraHandle in cameraList:
            (status, camInfo) = KYFG_CameraInfo2(cameraHandle)
            (status, streamHandle) = KYFG_StreamCreateAndAlloc(cameraHandle, 16, 0)
            streamHandleList.append(streamHandle)
        print(streamHandleList)
        for cameraHandle in cameraList:
            (status,) = KYFG_CameraStart(cameraHandle, streamHandleList[cameraList.index(cameraHandle)], 0)
        time.sleep(round(testTime/2))
        # Activate IO interrupt
        for cameraHandle in cameraList:
            (status,camInfo)=KYFG_CameraInfo2(cameraHandle)
            try:
                (status, fps) = KYFG_GetCameraValueFloat(cameraHandle, "AcquisitionFrameRate")
                print('set AcquisitionFrameRate for', camInfo.deviceModelName)
                (status, Width) = KYFG_GetCameraValueInt(cameraHandle, "Width")
                print('set Width', camInfo.deviceModelName)
                (status, Height) = KYFG_GetCameraValueInt(cameraHandle, "Height")
                print('set Height', camInfo.deviceModelName)
                (status,) = KYFG_SetGrabberValueEnum(grabberHandle, "TriggerMode", 1)
                print('set TriggerMode', camInfo.deviceModelName)
                (status,) = KYFG_SetGrabberValueFloat(grabberHandle, "TimerDuration", 100000.0)
                print('set TimerDuration', camInfo.deviceModelName)
                (status,) = KYFG_SetGrabberValueFloat(grabberHandle, "TimerDelay", 100000.0)
                print('set TimerDelay', camInfo.deviceModelName)
                (status,) = KYFG_SetGrabberValueEnum(grabberHandle, "TimerTriggerSource", 2)
                print('set TimerTriggerSource', camInfo.deviceModelName)
                (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "TriggerEventMode", 'AnyEdge')
                print('set TriggerEventMode', camInfo.deviceModelName)
            except: print('Not all settings are set on the camera')
        time.sleep(round(testTime/2))
        # Killing streams and closing cameras
        for cameraHandle in cameraList:
            (status, camInfo) = KYFG_CameraInfo2(cameraHandle)
            print('Stream stop for camera', camInfo.deviceModelName)
            (status,) = KYFG_CameraStop(cameraHandle)
            (status,) = KYFG_StreamDelete(streamHandleList[cameraList.index(cameraHandle)])
            (status,) = KYFG_CameraClose(cameraHandle)


    (status,) = KYFG_Close(grabberHandle)
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

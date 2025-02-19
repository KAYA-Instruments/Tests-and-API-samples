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
    return parser

def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)
aux_timestamps = []
stream_timestamp = []

def streamCallbackFunc(bufferHandle, userContext):
    global stream_timestamp
    try:
        (status,timestamp,pSize,pType)=KYFG_BufferGetInfo(bufferHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_TIMESTAMP)
        stream_timestamp.append(timestamp)
    except:
        pass
def auxCallbackFunc(bufferHandle, userContext):
    global aux_timestamps
    io_aux_data_p = cast(bufferHandle, ctypes.POINTER(KYFG_IO_AUX_DATA_C_STYLE))
    timestamp=io_aux_data_p.contents.timestamp
    aux_timestamps.append(timestamp)
def is_approximately_equal(num1, num2, tolerance_percent):
    tolerance = tolerance_percent / 100.0
    diff = abs(num1 - num2)
    avg = (abs(num1) + abs(num2)) / 2.0
    return diff <= avg * tolerance
def waitFortime(time_for_sleep):
    threadSleepSeconds = time_for_sleep
    print(f"Thread sleep for {threadSleepSeconds} seconds: ")
    for remaining in range(threadSleepSeconds, 0, -1):
        sys.stdout.write("\r")
        sys.stdout.write("{:2d} seconds remaining".format(remaining))
        sys.stdout.flush()
        time.sleep(1)
    sys.stdout.write("\rComplete!            \n")
    return threadSleepSeconds

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
    (grabberHandle,)=KYFG_Open(device_index)
    device_info = device_infos[device_index]
    global aux_timestamps
    global stream_timestamp

    print(
        f'Opened device [{device_index}]: (PCI {device_info.nBus}:{device_info.nSlot}:{device_info.nFunction})"{device_info.szDeviceDisplayName}"')
    (status,camHandleArray_col)=KYFG_UpdateCameraList(grabberHandle)
    if len(camHandleArray_col)==0:
        return CaseReturnCode.NO_HW_FOUND
    error_count=0
    for cameraHandle in camHandleArray_col:
        aux_timestamps=[]
        stream_timestamp=[]
        (status, camInfo) = KYFG_CameraInfo2(cameraHandle)
        (status,)=KYFG_CameraOpen2(cameraHandle,None)
        print(f'\n\nCamera {camInfo.deviceModelName} is open')
        # Set up the timer to have the required FPS
        # (status,fpsMax)=KYFG_GetCameraValueFloat(cameraHandle, "AcquisitionFrameRateMax")
        # check trigger mode
        try:
            if KYFG_IsGrabberValueImplemented(grabberHandle, 'TriggerMode'):
                KYFG_SetGrabberValueEnum(grabberHandle, "TriggerMode", 0)
            if KYFG_IsCameraValueImplemented(cameraHandle, "TriggerMode"):
                KYFG_SetCameraValueEnum(cameraHandle, "TriggerMode", 0)
            if KYFG_IsCameraValueImplemented(cameraHandle, "SimulationTriggerMode"):
                KYFG_SetCameraValueEnum(cameraHandle, "SimulationTriggerMode", 0)
        except:
            pass

        # (status,) = KYFG_SetCameraValueFloat(cameraHandle, "AcquisitionFrameRate", fpsMax*0.95)
        (status, fps) = KYFG_GetCameraValueFloat(cameraHandle, "AcquisitionFrameRate")
        print(f'FPS: {fps}')
        timer_period = 1000000 / (fps*2 )
        print(f'timer_period {timer_period}')
        (status,) = KYFG_SetGrabberValueEnum(grabberHandle, "TimerSelector", 0)
        (status,) = KYFG_SetGrabberValueFloat(grabberHandle, "TimerDelay", timer_period)
        (status,) = KYFG_SetGrabberValueFloat(grabberHandle, "TimerDuration", timer_period)
        (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "TimerEventMode", 'RisingEdge')
        # Set up the trigger:

        # FG parameters:
        (status,) = KYFG_SetGrabberValueInt(grabberHandle, "CameraSelector", 0)
        (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "CameraTriggerActivation", 'AnyEdge')
        (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "CameraTriggerSource", f'KY_TIMER_ACTIVE_0')
        (status,) = KYFG_SetGrabberValueEnum(grabberHandle, "CameraTriggerMode", 1)
        (status,) = KYFG_SetGrabberValueEnum(grabberHandle, "TriggerMode", 1)

        # Camera Parameters:
        if 'Chameleon' not in camInfo.deviceModelName:
            if KYFG_IsGrabberValueImplemented(cameraHandle, 'TriggerMode'):
                (status,) = KYFG_SetCameraValueEnum(cameraHandle, "TriggerMode", 0)
                KYFG_SetCameraValueEnum(cameraHandle, "ExposureAuto", 0)
                (status,) = KYFG_SetCameraValueFloat(cameraHandle, "ExposureTime", timer_period)
            else:
                continue
        else:
            (status,) = KYFG_SetCameraValueEnum(cameraHandle, "SimulationTriggerMode", 0)


        (status,streamHandle)=KYFG_StreamCreateAndAlloc(cameraHandle,16,0)
        (status,) = KYFG_StreamBufferCallbackRegister(streamHandle,streamCallbackFunc, None)
        (status,) = KYFG_AuxDataCallbackRegister(grabberHandle,auxCallbackFunc, None)

        (status,) = KYFG_CameraStart(cameraHandle,streamHandle,0)
        (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "TimerTriggerSource", 'KY_CONTINUOUS')
        waitFortime(1)
        (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "TimerTriggerSource", 'KY_DISABLED')
        (status,) = KYFG_CameraStop(cameraHandle)
        (status,) = KYFG_StreamBufferCallbackUnregister(streamHandle, streamCallbackFunc)
        (status,) = KYFG_AuxDataCallbackUnregister(grabberHandle,auxCallbackFunc)
        (status,) = KYFG_StreamDelete(streamHandle)
        (status,) = KYFG_CameraClose(cameraHandle)
        print(f'Camera {camInfo.deviceModelName} is close')
        print('Stream callbacks: ', len(stream_timestamp))
        print('AUX callbacks: ',len(aux_timestamps))


        assert len(aux_timestamps)>0, 'No AUX callbacks getted'
        for i in range(min(len(stream_timestamp),len(aux_timestamps))):
            if not is_approximately_equal(stream_timestamp[i], aux_timestamps[i], 0.1):
                print('Timestamps AUX and stream is not equals')
                print(stream_timestamp[i], aux_timestamps[i])
                error_count += 1
        print('error_count', error_count)
    (status,) = KYFG_Close(grabberHandle)
    assert error_count == 0, 'There are errors while test'
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
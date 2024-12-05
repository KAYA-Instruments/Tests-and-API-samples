# Default KAYA import
import sys
import os
import argparse

sys.path.insert(0, os.environ['KAYA_VISION_POINT_PYTHON_PATH'])
from KYFGLib import *
from enum import IntEnum  # for CaseReturnCode


# Common Case imports
import time


def CaseArgumentParser():
    parser = argparse.ArgumentParser()
    # Standard arguments for all tests
    parser.add_argument('--unattended', default=False, action='store_true', help='Do not interact with user')
    parser.add_argument('--no-unattended', dest='unattended', action='store_false')
    parser.add_argument('--deviceList', default=False, action='store_true',
                        help='Print list of available devices and exit')
    parser.add_argument('--deviceIndex', type=int, default=-1,
                        help='Index of PCI device to use, '
                             'run this script with "--deviceList" to see available devices and exit')
    return parser


def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)


###################### Callback Function ####################################
class StreamInfoStruct:
    def __init__(self):
        self.callbackCount = 0
        self.instantsFPS = []
        return


def Stream_callback_func(buffHandle, userContext):
    userContext.callbackCount += 1
    try:
        (status, instantfps, pInfoSize, pInfoType) = KYFG_BufferGetInfo(buffHandle,
                                                                        KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_INSTANTFPS)
        userContext.instantsFPS.append(instantfps)
    except:
        pass

    return


def is_approximately_equal(num1, num2, tolerance_percent):
    tolerance = tolerance_percent / 100.0
    diff = abs(num1 - num2)
    avg = (abs(num1) + abs(num2)) / 2.0
    return diff <= avg * tolerance


def WaitForSleep(sleepTime):
    threadSleepSeconds = sleepTime
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

    # Standard arguments for all case_NNNN
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
    errorCount = 0
    (grabber_handle,) = KYFG_Open(device_index)
    (status, camHandleArray) = KYFG_UpdateCameraList(grabber_handle)
    assert len(camHandleArray) != 0, 'There is no cameras onn this grabber'
    camerasWithTriggerMode = False
    for cameraIndex, cameraHandle in enumerate(camHandleArray):
        (status, camInfo) = KYFG_CameraInfo2(cameraHandle)
        print(f"Camera model {str(camInfo.deviceModelName)} fw {str(camInfo.deviceFirmwareVersion)} is opened")
        (status,) = KYFG_CameraOpen2(cameraHandle, None)
        try:
            if KYFG_IsCameraValueImplemented(cameraHandle, "TriggerMode"):
                (status,) = KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "TriggerMode", "On")
                (status,) = KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "TriggerSource", "LinkTrigger0")
            else:
                (status,) = KYFG_SetCameraValueEnum(cameraHandle, "SimulationTriggerMode", 1)
                (status,) = KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "SimulationTriggerSource", "KY_CAM_TRIG")
            camerasWithTriggerMode = True
        except:
            print(f'There is no "TriggerMode" on camera {camInfo.deviceModelName}"')
            (status,) = KYFG_CameraClose(cameraHandle)
            continue
        frame_fps_max = 0
        frame_fps = 0
        (status, frame_fps_max) = KYFG_GetCameraValueFloat(cameraHandle, "AcquisitionFrameRateMax")
        (status, frame_fps) = KYFG_GetCameraValueFloat(cameraHandle, "AcquisitionFrameRate")
        if frame_fps_max == 0:
            frame_fps = frame_fps
        else:
            frame_fps = frame_fps_max
        FRAME_PERIOD_USEC = (1e6 / frame_fps)*0.9
        timer_per_delay = FRAME_PERIOD_USEC / 2

        # Set up timer and triggers
        (status,) = KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "ExposureAuto", "Off")
        (status,) = KYFG_SetCameraValueFloat(cameraHandle, "ExposureTime", FRAME_PERIOD_USEC)
        (status,) = KYFG_SetGrabberValueInt(grabber_handle, "CameraSelector", cameraIndex)
        (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabber_handle, "TimerSelector", "Timer0")
        (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabber_handle, "TimerTriggerSource", "KY_DISABLED")
        (status,) = KYFG_SetGrabberValueFloat(grabber_handle, "TimerDelay", timer_per_delay)
        (status,) = KYFG_SetGrabberValueFloat(grabber_handle, "TimerDuration", timer_per_delay)
        (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabber_handle, "TimerActivation", "RisingEdge")
        (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabber_handle, "CameraTriggerSource", "KY_TIMER_ACTIVE_0")
        (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabber_handle, "CameraTriggerActivation", "AnyEdge")
        (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabber_handle, "CameraTriggerMode", "On")
        
        # Create stream
        (status, cameraStreamHandle) = KYFG_StreamCreateAndAlloc(cameraHandle, 16, 0)
        stream_info_struct = StreamInfoStruct()
        (KYFG_StreamBufferCallbackRegister_status,) = KYFG_StreamBufferCallbackRegister(cameraStreamHandle,
                                                                                        Stream_callback_func,
                                                                                        stream_info_struct)

        # Start camera
        (status,) = KYFG_CameraStart(cameraHandle, cameraStreamHandle, 0)
        (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabber_handle, "TimerTriggerSource", "KY_CONTINUOUS")
        duration = 5

        WaitForSleep(duration)

        (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabber_handle, "TimerTriggerSource", "KY_DISABLED")
        (status,) = KYFG_CameraStop(cameraHandle)
        (status, droped_frame_counter) = KYFG_GetGrabberValueInt(grabber_handle, "DropFrameCounter")
        # Checking results
        for i in stream_info_struct.instantsFPS[1:]:
            if not is_approximately_equal(i, frame_fps, 10):
                print("Acquired FPS does not match FPS calculated by the grabber")
                print(f"Calculated FPS {frame_fps}\nActual FPS {i}\n")
                errorCount += 1

        print(f'Drop Frames: {droped_frame_counter}')
        print(f'frame_counter: {stream_info_struct.callbackCount}')
        if droped_frame_counter != 0:
            print('There are dropped frames')
            errorCount += 1

        print(f'\nExiting from CaseRun({args}) with code 0...')

        KYFG_StreamBufferCallbackUnregister(cameraStreamHandle, Stream_callback_func)
        KYFG_StreamDelete(cameraStreamHandle)
        KYFG_CameraClose(cameraHandle)
    assert errorCount == 0, 'There are some errors on cameras'
    assert camerasWithTriggerMode == True, 'No cameras with trigger mode on this grabber'
    KYFG_Close(grabber_handle)
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

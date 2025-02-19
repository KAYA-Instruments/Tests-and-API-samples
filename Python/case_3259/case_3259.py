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

    parser.add_argument('--segmentsperbuffer', type=int, default=16, help='segmentsperbuffer')
    parser.add_argument('--cameraModel', default='Iron255C', type=str, help='Camera model')

    return parser


camHandleArray = {}

class StreamCallbackStructure:
    def __init__(self) -> None:
        self.period = 0
        self.callbackCount = 0
        self.last_timestamp = 0

def Stream_Callback_func(buffHandle, userContext):
    if buffHandle == 0:
        return
    print('Good callback streams buffer handle: ' + str(buffHandle))

    (KYFG_BufferGetInfo_status, pInfoTimestamp, pInfoSize, pInfoType) = KYFG_BufferGetInfo(
        buffHandle,
        KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_TIMESTAMP
    )
    
    if not userContext.last_timestamp:
        userContext.last_timestamp = pInfoTimestamp
    else:
        userContext.period = pInfoTimestamp - userContext.last_timestamp

    userContext.callbackCount += 1

def check_is_camera_available(deviceModelName, camHandles):
    cams_num = len(camHandles)
    for i in range(cams_num):
        cameraHandle = camHandles[i]
        (Status, camInfo) = KYFG_CameraInfo2(cameraHandle)

        if deviceModelName == camInfo.deviceModelName:
            return True
    return False


def start_stream(grabberHandle, camHandle, segmentsperbuffer = 1):
    (status,) = KYFG_CameraOpen2(camHandle, None)
    (status, fps_max, fps_min) = KYFG_GetCameraValueFloatMaxMin(camHandle, "AcquisitionFrameRate")
    
    # Set "AcquisitionFrameRate" of the camera to 100
    frame_rate = fps_max if fps_max <= 100 else 100
    (status,) = KYFG_SetCameraValueFloat(camHandle, "AcquisitionFrameRate", float(frame_rate))

    # Set "SegmentsPerBuffer" on grabber side
    KYFG_SetGrabberValueInt(grabberHandle, "SegmentsPerBuffer", segmentsperbuffer)
    
    # Create stream and get buffer size
    (_, streamHandle) = KYFG_StreamCreateAndAlloc(camHandle, 2, 0)
    (status, buffSize, frameDataSize, pInfoType) = KYFG_StreamGetInfo(streamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_PAYLOAD_SIZE)

    streamCallbackStruct = StreamCallbackStructure()
    (status,) = KYFG_StreamBufferCallbackRegister(streamHandle, Stream_Callback_func, streamCallbackStruct)
    
    KYFG_CameraStart(camHandle, streamHandle, 2)

    time.sleep(5)

    KYFG_CameraStop(camHandle)
    KYFG_StreamBufferCallbackUnregister(streamHandle, Stream_Callback_func)
    KYFG_StreamDelete(streamHandle)
    KYFG_CameraClose(camHandle)

    return streamCallbackStruct.period, buffSize




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

    segmentsperbuffer = args['segmentsperbuffer']
    cameraModel = args['cameraModel']
    # Check grabber
    (status, device_info) = KY_DeviceInfo(device_index)
    if device_info.m_Protocol != KY_DEVICE_PROTOCOL.KY_DEVICE_PROTOCOL_CoaXPress:
        print('Test could not run on this grabber')
        return CaseReturnCode.COULD_NOT_RUN
    (grabberHandle,) = KYFG_Open(device_index)
    (_, camHandleArray[device_index]) = KYFG_UpdateCameraList(grabberHandle)
    camHandle=0
    if cameraModel == "AnyCamera":
        camHandle = camHandleArray[device_index][0]
    else:
        for cameraHandle in camHandleArray[device_index]:
            (status, camInfo) = KYFG_CameraInfo2(cameraHandle)
            if camInfo.deviceModelName==cameraModel:
                camHandle=cameraHandle
        if camHandle == 0:
            print(f'There is no camera {cameraModel} on grabber')
            return CaseReturnCode.NO_HW_FOUND
    # if not check_is_camera_available(cameraModel, camHandleArray[device_index]):
    #     KYFG_Close(grabberHandle)
    #     print(f"\nRequired camera {cameraModel} not found")
    #     return CaseReturnCode.NO_HW_FOUND

    print("cameras count is ", len(camHandleArray[device_index]))
    # check trigger mode
    try:
        if KYFG_IsGrabberValueImplemented(grabberHandle, 'TriggerMode'):
            KYFG_SetGrabberValueEnum(grabberHandle, "TriggerMode", 0)
        if KYFG_IsCameraValueImplemented(camHandle, "TriggerMode"):
            KYFG_SetCameraValueEnum(camHandle, "TriggerMode", 0)
        if KYFG_IsCameraValueImplemented(camHandle, "SimulationTriggerMode"):
            KYFG_SetCameraValueEnum(camHandle, "SimulationTriggerMode", 0)
    except:
        pass
    # First period
    (status, camInfo) = KYFG_CameraInfo2(camHandle)
    print(f'Camera {camInfo.deviceModelName} is open')

    stream_period_1, biffSeze_1 = start_stream(grabberHandle, camHandle)

    # Second period
    stream_period_2, biffSeze_2 = start_stream(grabberHandle, camHandle, segmentsperbuffer)
    period2 = stream_period_2 / segmentsperbuffer
    print("data", biffSeze_1, biffSeze_2, stream_period_1, period2)

    assert (period2 - period2 / 100) <= stream_period_1 <= (period2 + period2 / 100), 'periods error'
    assert biffSeze_1 == biffSeze_2 / segmentsperbuffer, f'biffSeze_1 ({biffSeze_1}) not equal to biffSeze_2 ({biffSeze_2}) / segmentsperbuffer ({segmentsperbuffer})'

    KYFG_Close(grabberHandle)
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
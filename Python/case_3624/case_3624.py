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
    parser.add_argument('--cameraModel', type=str, default='Iron2020eM')
    parser.add_argument('--number_of_tests', type=int, default=10)

    return parser

class StreamStruct:
    def __init__(self):
        self.callbackCounter = 0
        return

def streamCallbackFunction(buffHandle, userContext):
    userContext.callbackCounter += 1
    try:
        (status,) = KYFG_BufferToQueue(buffHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
    except:
        pass
def eventCallback(userContext, camStartRequestObj):
    if camStartRequestObj.deviceEvent.eventId == KYDEVICE_EVENT_ID.KYDEVICE_EVENT_CAMERA_CONNECTION_LOST_ID:
        (status,) = KYFG_CameraClose(camStartRequestObj.camHandle)

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
    number_of_tests = args['number_of_tests']
    camera_model = args['cameraModel']
    number_of_buffers = 16
    error_count = 0
    (status, device_info) = KY_DeviceInfo(device_index)
    if device_info.m_Protocol != KY_DEVICE_PROTOCOL.KY_DEVICE_PROTOCOL_CoaXPress:
        return CaseReturnCode.COULD_NOT_RUN
    (grabberHandle,) = KYFG_Open(device_index)
    camera_on_grabber = None
    KYDeviceEventCallBackRegister(grabberHandle, eventCallback, None)
    for i in range(number_of_tests):
        print(f'\nTest number {i+1}')
        (status, cameraList) = KYFG_UpdateCameraList(grabberHandle)
        assert len(cameraList), 'No cameras detected'
        cameraHandle = None
        for cam in cameraList:
            (status, camInfo) = KYFG_CameraInfo2(cam)
            if camInfo.deviceModelName == camera_model:
                cameraHandle = cam
                break
        if camera_on_grabber is None:
            if cameraHandle is None:
                return CaseReturnCode.NO_HW_FOUND
            else:
                camera_on_grabber = True
        else:
            assert cameraHandle is not None, f'Camera not detected while {i} iteration'
        (status, camInfo) = KYFG_CameraInfo2(cameraHandle)
        (status,) = KYFG_CameraOpen2(cameraHandle, None)
        if KYFG_IsGrabberValueImplemented(grabberHandle, "TriggerMode"):
            KYFG_SetGrabberValueEnum(grabberHandle, "TriggerMode", 0)
        if KYFG_IsCameraValueImplemented(cameraHandle, "TriggerMode"):
            KYFG_SetCameraValueEnum(cameraHandle, "TriggerMode", 0)
        KYFG_SetGrabberValueInt(grabberHandle, "CameraSelector", cameraList.index(cameraHandle))
        print(f'Start test for camera {camInfo.deviceModelName}')
        (status, streamHandle) = KYFG_StreamCreate(cameraHandle, 0)
        stream_struct = StreamStruct()
        (status,) = KYFG_StreamBufferCallbackRegister(streamHandle, streamCallbackFunction, stream_struct)
        (status, pInfoBuffer, pInfoSize, pInfoType) = KYFG_StreamGetInfo(streamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_PAYLOAD_SIZE)
        streamBuffersHandle = [0 for i in range(int(number_of_buffers))]
        for IFrame in range(number_of_buffers):
            (status,  streamBuffersHandle[i]) = KYFG_BufferAllocAndAnnounce(streamHandle, pInfoBuffer, 0)
        (status,) = KYFG_BufferQueueAll(streamHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_UNQUEUED, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
        (status,) = KYFG_CameraStart(cameraHandle, streamHandle, 0)
        time.sleep(2)
        (status, frame_counter) = KYFG_GetGrabberValueInt(grabberHandle, "RXFrameCounter")
        if not frame_counter or not stream_struct.callbackCounter:
            print('ERROR! Acquisition is not started')
            print(f'callbackCounter: {stream_struct.callbackCounter} frame_counter {frame_counter}')
            error_count += 1
        KYFG_GrabberExecuteCommand(grabberHandle, "CxpPoCxpTurnOff")
        time.sleep(10)
        KYFG_GrabberExecuteCommand(grabberHandle, "CxpPoCxpAuto")
        time.sleep(24)
    KYFG_GrabberExecuteCommand(grabberHandle, "CxpPoCxpAuto")
    time.sleep(10)
    (status,) = KYFG_Close(grabberHandle)
    assert not error_count, "Test not passed"




    print(f'\nExiting from CaseRun({args}) with code SUCCESS...')
    return CaseReturnCode.SUCCESS


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

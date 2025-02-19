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

def streamCallbackFunction(buffHandle, userContext):
    if buffHandle == 0:
        return
    try:
        (status,) = KYFG_BufferToQueue(buffHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
    except:
        return
    return

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
    (status, device_info) = KY_DeviceInfo(device_index)
    if device_info.m_Protocol != KY_DEVICE_PROTOCOL.KY_DEVICE_PROTOCOL_CoaXPress:
        print('Test could not run on this grabber')
        return CaseReturnCode.COULD_NOT_RUN
    (grabberHandle,) = KYFG_Open(device_index)
    (status, camList) = KYFG_UpdateCameraList(grabberHandle)
    error_count = 0
    for i in range(len(camList)):
        cameraHandle = camList[i]
        (status, camInfo) = KYFG_CameraInfo2(cameraHandle)
        (status,) = KYFG_CameraOpen2(cameraHandle, None)
        print(f"\n\nCamera {camInfo.deviceModelName} is open")
        try:
            (status, isSharingSupported) = KYFG_GetGrabberValueInt(grabberHandle, 'SWCapable_InterProcessSharing_Imp')
            if not isSharingSupported:
                print('Grabber sharing is not supported on this device')
                (status,) = KYFG_Close(grabberHandle)
                return CaseReturnCode.COULD_NOT_RUN
        except:
            print('Grabber sharing is not supported on this device')
            (status,) = KYFG_Close(grabberHandle)
            return CaseReturnCode.COULD_NOT_RUN
        (status, streamHandle) = KYFG_StreamCreate(cameraHandle, 0)
        (status,) = KYFG_StreamBufferCallbackRegister(streamHandle, streamCallbackFunction, None)
        (status, payload_size, _, _) = KYFG_StreamGetInfo(streamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_PAYLOAD_SIZE)
        number_of_buffers = [0 for i in range(16)]
        for iFrame in range(len(number_of_buffers)):
            (status, number_of_buffers[iFrame]) = KYFG_BufferAllocAndAnnounce(streamHandle, payload_size, 0)
        (status,) = KYFG_BufferQueueAll(streamHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_UNQUEUED, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
        (status,) = KYFG_CameraStart(cameraHandle, streamHandle, 0)
        time.sleep(2)
        KYFG_SetGrabberValueEnum(grabberHandle, "TriggerMode", 1)  # for increase drop frame counter
        time.sleep(2)
        KYFG_SetGrabberValueEnum(grabberHandle, "TriggerMode", 0)
        (status,) = KYFG_CameraStop(cameraHandle)
        KYFG_SetGrabberValueInt(grabberHandle, "CameraSelector", i)
        (status, RXPacketCounter) = KYFG_GetGrabberValueInt(grabberHandle, "RXPacketCounter")
        (status, DropPacketCounter) = KYFG_GetGrabberValueInt(grabberHandle, "DropPacketCounter")
        (status, RXFrameCounter) = KYFG_GetGrabberValueInt(grabberHandle, "RXFrameCounter")
        (status, DropFrameCounter) = KYFG_GetGrabberValueInt(grabberHandle, "DropFrameCounter")
        (status, CRCErrorCounter) = KYFG_GetGrabberValueInt(grabberHandle, "CRCErrorCounter")
        (status, DropStreamIdCounter) = KYFG_GetGrabberValueInt(grabberHandle, "DropStreamIdCounter")
        print('\nStatistic before reset')
        print(f'RXPacketCounter {RXPacketCounter}')
        print(f'DropPacketCounter {DropPacketCounter}')
        print(f'RXFrameCounter {RXFrameCounter}')
        print(f'DropFrameCounter {DropFrameCounter}')
        print(f'CRCErrorCounter {CRCErrorCounter}')
        print(f'DropStreamIdCounter {DropStreamIdCounter}')
        if (RXPacketCounter == 0 and DropPacketCounter == 0) or (RXFrameCounter == 0 and DropFrameCounter == 0):
            print('Acquisition is not started')
            error_count += 1
        KYFG_GrabberExecuteCommand(grabberHandle, "StatisticsCountersReset")
        time.sleep(1)
        (status, RXPacketCounter) = KYFG_GetGrabberValueInt(grabberHandle, "RXPacketCounter")
        (status, DropPacketCounter) = KYFG_GetGrabberValueInt(grabberHandle, "DropPacketCounter")
        (status, RXFrameCounter) = KYFG_GetGrabberValueInt(grabberHandle, "RXFrameCounter")
        (status, DropFrameCounter) = KYFG_GetGrabberValueInt(grabberHandle, "DropFrameCounter")
        (status, CRCErrorCounter) = KYFG_GetGrabberValueInt(grabberHandle, "CRCErrorCounter")
        (status, DropStreamIdCounter) = KYFG_GetGrabberValueInt(grabberHandle, "DropStreamIdCounter")

        print('\nStatistic after reset')
        print(f'RXPacketCounter {RXPacketCounter}')
        print(f'DropPacketCounter {DropPacketCounter}')
        print(f'RXFrameCounter {RXFrameCounter}')
        print(f'DropFrameCounter {DropFrameCounter}')
        print(f'CRCErrorCounter {CRCErrorCounter}')
        print(f'DropStreamIdCounter {DropStreamIdCounter}')
        if RXPacketCounter != DropPacketCounter != RXFrameCounter != DropFrameCounter != CRCErrorCounter != DropStreamIdCounter != 0:
            print("Statistic reset is unsuccessfully")
            error_count += 1
        (status,) = KYFG_StreamBufferCallbackUnregister(streamHandle, streamCallbackFunction)
        (status,) = KYFG_StreamDelete(streamHandle)
        (status,) = KYFG_CameraClose(cameraHandle)
    (status,) = KYFG_Close(grabberHandle)
    assert error_count == 0, 'Test not passed'

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

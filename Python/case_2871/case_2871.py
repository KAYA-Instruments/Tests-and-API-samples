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


def streamCallbackFunction(buffHandle, userContext):
    if buffHandle == NULL_STREAM_BUFFER_HANDLE or buffHandle == INVALID_STREAM_BUFFER_HANDLE:
        return
    try:
        (status,) = KYFG_BufferToQueue(buffHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
    except:
        return
    return


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
    error_count = 0
    (status, device_info) = KY_DeviceInfo(device_index)
    if device_info.m_Protocol != KY_DEVICE_PROTOCOL.KY_DEVICE_PROTOCOL_CoaXPress:
        print('Test could not run on this grabber')
        return CaseReturnCode.COULD_NOT_RUN
    (grabberHandle,) = KYFG_Open(device_index)
    (status, first_cameraList) = KYFG_UpdateCameraList(grabberHandle)
    print(f"first_cameraList: {len(first_cameraList)} cameras found")
    if len(first_cameraList) < 2:
        print('There is not enough cameras for this test')
        return CaseReturnCode.NO_HW_FOUND
    (status, camInfo) = KYFG_CameraInfo2(first_cameraList[0])
    KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "CxpPoCxpHostConnectionSelector", "All")
    (status,) = KYFG_GrabberExecuteCommand(grabberHandle, "CxpPoCxpTurnOff")
    (status,) = KYFG_SetGrabberValueEnum(grabberHandle, "CxpPoCxpHostConnectionSelector", camInfo.link_mask)
    (status,) = KYFG_GrabberExecuteCommand(grabberHandle, "CxpPoCxpAuto")
    for i in range(2):
        (status, second_cameraList) = KYFG_UpdateCameraList(grabberHandle)
        print(f"{'second_cameraList' if i == 0 else 'third_cameraList'}: {len(second_cameraList)} cameras found")
        if i == 0:
            if len(second_cameraList) != 1:
                print("CxpPoCxpHostConnectionSelector is not working correctly")
                error_count+=1
        else:
            if len(second_cameraList) != len(first_cameraList):
                print("CxpPoCxpHostConnectionSelector is not working correctly")
                error_count+=1
        for c in range(len(second_cameraList)):
            # Stream creation
            cameraHandle = second_cameraList[c]
            (status,) = KYFG_CameraOpen2(cameraHandle, None)
            try:
                if KYFG_IsGrabberValueImplemented(grabberHandle, 'TriggerMode'):
                    KYFG_SetGrabberValueEnum(grabberHandle, "TriggerMode", 0)
                if KYFG_IsCameraValueImplemented(cameraHandle, "TriggerMode"):
                    KYFG_SetCameraValueEnum(cameraHandle, "TriggerMode", 0)
                if KYFG_IsCameraValueImplemented(cameraHandle, "SimulationTriggerMode"):
                    KYFG_SetCameraValueEnum(cameraHandle, "SimulationTriggerMode", 0)
            except:
                pass
            (status, streamHandle) = KYFG_StreamCreate(cameraHandle, 0)
            (status,) = KYFG_StreamBufferCallbackRegister(streamHandle, streamCallbackFunction, None)
            # Retrieve information about required frame buffer size and alignment
            (status, payload_size, _, _) = KYFG_StreamGetInfo(streamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_PAYLOAD_SIZE)
            (status, buf_allignment, _, _) = KYFG_StreamGetInfo(streamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_BUF_ALIGNMENT)
            # allocate memory for desired number of frame buffers
            streamBufferHandle = [0 for i in range(16)]
            streamAllignedBuffer = [0 for i in range(16)]
            for iFrame in range(len(streamBufferHandle)):
                streamAllignedBuffer[iFrame] = aligned_array(buf_allignment, c_ubyte, payload_size)
                # print("Address of alligned array: " + hex(addressof(streamAllignedBuffer[iFrame])))
                (status, streamBufferHandle[iFrame]) = KYFG_BufferAnnounce(streamHandle,
                                                                           streamAllignedBuffer[iFrame], None)

            (status,) = KYFG_BufferQueueAll(streamHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_UNQUEUED,
                                            KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
            (status,) = KYFG_CameraStart(cameraHandle, streamHandle, 0)
            time.sleep(3)
            (status,) = KYFG_CameraStop(cameraHandle)
            (status, drop_frame_counter) = KYFG_GetGrabberValueInt(grabberHandle, "DropFrameCounter")
            print("drop_frame_counter = ", drop_frame_counter)
            if drop_frame_counter > 0:
                error_count += 1
            (status,) = KYFG_StreamBufferCallbackUnregister(streamHandle, streamCallbackFunction)
            (status,) = KYFG_StreamDelete(streamHandle)
            (status,) = KYFG_CameraClose(cameraHandle)
        KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "CxpPoCxpHostConnectionSelector", "All")
        (status,) = KYFG_GrabberExecuteCommand(grabberHandle, "CxpPoCxpAuto")
    (status,) = KYFG_Close(grabberHandle)
    print('error_count = ', error_count)
    print(f'\nExiting from CaseRun({args}) with code SUCCESS...')


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

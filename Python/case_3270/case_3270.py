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
    parser.add_argument('--SimulationTriggerMode', type=str, default='Triggered')
    parser.add_argument('--SimulationTriggerActivation', type=str, default='RisingEdge')
    parser.add_argument('--SimulationTriggerSource', type=str, default='KY_SOFTWARE')
    parser.add_argument('--numberTriggerCalls', type=int, default=10)

    return parser


def Stream_callback_func(buffHandle, userContext):
    if (buffHandle == 0):
        Stream_callback_func.copyingDataFlag = 0

        return
    print('Good callback streams buffer handle: ' + str(buffHandle))
    (KYFG_BufferToQueue_status,) = KYFG_BufferToQueue(buffHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
    return

def system_initialization(device_index):
    # global grabber_handle
    (grabber_handle,) = KYFG_Open(device_index)

    (CameraScan_status, camHandleArray) = KYFG_UpdateCameraList(grabber_handle)
    camHandlerChameleon = -102;
    if (len(camHandleArray) == 0):
        print("No cameras found ...")
        return camHandlerChameleon
    for camHandle in camHandleArray:
        (Status, camInfo) = KYFG_CameraInfo2(camHandle)
        cameraName = camInfo.deviceModelName
        if "Chameleon" in cameraName:
            camHandlerChameleon = camHandle

    return camHandlerChameleon, grabber_handle

def setChameleonParams(camera_handle, simulationTriggerMode, simulationTriggerActivation,
                       simulationTriggerSource):
    KYFG_SetCameraValueEnum_ByValueName(camera_handle, "SimulationTriggerMode", simulationTriggerMode)
    KYFG_SetCameraValueEnum_ByValueName(camera_handle, "SimulationTriggerActivation", simulationTriggerActivation)
    KYFG_SetCameraValueEnum_ByValueName(camera_handle, "SimulationTriggerSource", simulationTriggerSource)


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

    # Other parameters used by this particular case
    numberTriggerCalls = args["numberTriggerCalls"]
    simulationTriggerMode = args["SimulationTriggerMode"]
    simulationTriggerActivation = args["SimulationTriggerActivation"]
    simulationTriggerSource = args["SimulationTriggerSource"]


    device_info = device_infos[device_index]
    print(f'Opened device [{device_index}]: (PCI {device_info.nBus}:{device_info.nSlot}:{device_info.nFunction})"{device_info.szDeviceDisplayName}"')

    camera_handle, grabber_handle = system_initialization(device_index)
    if camera_handle == -102:
        return CaseReturnCode.NO_HW_FOUND

    # Camera open and start
    (cam_open_status,) = KYFG_CameraOpen2(camera_handle, None)
    try:
        if KYFG_IsGrabberValueImplemented(grabber_handle, 'TriggerMode'):
            KYFG_SetGrabberValueEnum(grabber_handle, "TriggerMode", 0)
        if KYFG_IsCameraValueImplemented(camera_handle, "TriggerMode"):
            KYFG_SetCameraValueEnum(camera_handle, "TriggerMode", 0)
        if KYFG_IsCameraValueImplemented(camera_handle, "SimulationTriggerMode"):
            KYFG_SetCameraValueEnum(camera_handle, "SimulationTriggerMode", 0)
    except:
        pass
    # Here must be KYFG_SetCameraValue(), KYFG_SetGrabberValue() if it need
    setChameleonParams(camera_handle, simulationTriggerMode, simulationTriggerActivation, simulationTriggerSource)

    # create stream and assign appropriate runtime acquisition callback function
    (status, buff_handle) = KYFG_StreamCreate(camera_handle, 0)
    (status,) = \
        KYFG_StreamBufferCallbackRegister(buff_handle, Stream_callback_func, 0)
    # Retrieve information about required frame buffer size and alignment
    (status, payload_size, frameDataSize, pInfoType) = \
        KYFG_StreamGetInfo(buff_handle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_PAYLOAD_SIZE)


    for iFrame in range(16):
        (status, bufferhandle) = KYFG_BufferAllocAndAnnounce(buff_handle, payload_size, 0)

    (status,) = \
        KYFG_BufferQueueAll(buff_handle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_UNQUEUED,
                            KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)

    print('camera ready for start')
    (status,) = KYFG_CameraStart(camera_handle, buff_handle, 0)

    (status, RXFrameCounterBefore) = KYFG_GetGrabberValueInt(grabber_handle, "RXFrameCounter")
    for i in range(numberTriggerCalls):
        (status,) = KYFG_CameraExecuteCommand(camera_handle, "SimulationTriggerSoftware")
        time.sleep(1)
    (status, RXFrameCounterAfter) = KYFG_GetGrabberValueInt(grabber_handle, "RXFrameCounter")
    # assert RXFrameCounterAfter - RXFrameCounterBefore == 1, "Failed: number of lost frames - " + str(RXFrameCounterAfter - RXFrameCounterBefore)



    (CameraStop_status,) = KYFG_CameraStop(camera_handle)
    print('numberTriggerCalls = ', numberTriggerCalls, '  RXFrameCounterAfter = ', RXFrameCounterAfter)
    # close processing
    (CallbackRegister_status,) = KYFG_StreamBufferCallbackUnregister(buff_handle, Stream_callback_func)
    (KYFG_StreamDelete_status,) = KYFG_StreamDelete(buff_handle)
    (status,) = KYFG_CameraClose(camera_handle)
    #Close the device used for this test
    (status, ) = KYFG_Close(grabber_handle)  # TODO: If Chameleon selected then without this call: Process finished with exit code -1073740791 (0xC0000409)
    print('RXFrameCounterAfter', RXFrameCounterAfter)
    print('numberTriggerCalls', numberTriggerCalls)
    assert (RXFrameCounterAfter == numberTriggerCalls), "Failed: Number of frames is not equal to the number of " \
                                                              "triggers sent"

    print(f'Closed device [{device_index}]: (PCI {device_info.nBus}:{device_info.nSlot}:{device_info.nFunction})"{device_info.szDeviceDisplayName}"')



    print(f'\nExiting from CaseRun({args}) with code SUCCESS...')
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

# Common KAYA imports DO NOT EDIT!!!
import sys
import os
import argparse
import time
sys.path.insert(0, os.environ['KAYA_VISION_POINT_PYTHON_PATH'])
from KYFGLib import *

# Common Case imports DO NOT EDIT!!!
from enum import IntEnum  # for CaseReturnCode

# additional imports required by particular case, ADD CASE SPECIFIC IMPORTS UNDER THIS LINE:


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

class CameraParameter:
    def __init__(self, paramName):
        self.paramName = paramName
        self.ParamValues = []
        self.getEnumEntries = False

class StreamCallbackStruct:
    def __init__(self):
        self.callbackCounter = 0
def cameraParametersCallback(userContext, pParameterDescriptorPtr, grouppingLevel):
    cameraParameter = cast(userContext, py_object).value
    if cameraParameter.getEnumEntries == True:
        if pParameterDescriptorPtr.interfaceType != ParameterInterfaceType.IEnumEntry:
            cameraParameter.getEnumEntries = False
        else:
            cameraParameter.ParamValues.append(pParameterDescriptorPtr.paramName)
    if str(pParameterDescriptorPtr.paramName) == cameraParameter.paramName:
        cameraParameter.getEnumEntries = True

def streamCallbackFunction(buffHandle, userContext):
    if buffHandle == NULL_STREAM_BUFFER_HANDLE or buffHandle == INVALID_STREAM_BUFFER_HANDLE:
        return
    userContext.callbackCounter += 1
    try:
        (status,) = KYFG_BufferToQueue(buffHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
    except:
        pass
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
    (status, cameraList) = KYFG_UpdateCameraList(grabberHandle)
    assert len(cameraList) > 0, "There are no cameras on this list"
    error_count = 0
    for cameraHandle in cameraList:
        (status,) = KYFG_CameraOpen2(cameraHandle, None)
        (status, camInfo) = KYFG_CameraInfo2(cameraHandle)
        print(f"\nCamera {camInfo.deviceModelName} is open")
        connection_config_obj = CameraParameter("ConnectionConfig")
        pixel_format_obj = CameraParameter("PixelFormat")
        KY_RegisterCameraConfigurationParameterCallback(cameraHandle, cameraParametersCallback,
                                                        py_object(connection_config_obj))
        KY_GetCameraConfigurationParameterDefinitions(cameraHandle)
        KY_UnregisterCameraConfigurationParameterCallback(cameraHandle, cameraParametersCallback)
        KY_RegisterCameraConfigurationParameterCallback(cameraHandle, cameraParametersCallback,
                                                        py_object(pixel_format_obj))
        KY_GetCameraConfigurationParameterDefinitions(cameraHandle)
        KY_UnregisterCameraConfigurationParameterCallback(cameraHandle, cameraParametersCallback)
        for connectionConfig in connection_config_obj.ParamValues:
            (status,) = KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "ConnectionConfig", connectionConfig)
            print(f'ConnectionConfig: {connectionConfig}')
            for pixel_format in pixel_format_obj.ParamValues:
                KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "PixelFormat", pixel_format)
                print(f'PixelFormat {pixel_format}')
                (stream_create_status, streamHandle) = KYFG_StreamCreate(cameraHandle, 0)
                if stream_create_status != FGSTATUS_OK:
                    print('Stream is not created correctly')
                    error_count += 1
                streamStruct = StreamCallbackStruct()
                (status,) = KYFG_StreamBufferCallbackRegister(streamHandle, streamCallbackFunction, streamStruct)
                (status, payloadSize, _, _) = KYFG_StreamGetInfo(streamHandle,
                                                                 KY_STREAM_INFO_CMD.KY_STREAM_INFO_PAYLOAD_SIZE)
                buffersArray = [0 for i in range(16)]
                for iFrame in range(len(buffersArray)):
                    (status, buffersArray[iFrame]) = KYFG_BufferAllocAndAnnounce(streamHandle, payloadSize, 0)
                (status,) = KYFG_BufferQueueAll(streamHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_UNQUEUED,
                                                KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
                (status,) = KYFG_CameraStart(cameraHandle, streamHandle, 0)
                time.sleep(3)
                (status,) = KYFG_CameraStop(cameraHandle)
                (status,) = KYFG_StreamBufferCallbackUnregister(streamHandle, streamCallbackFunction)
                (status,) = KYFG_StreamDelete(streamHandle)
                if streamStruct.callbackCounter == 0:
                    print('Stream not started')
                    error_count += 1
        (status,) = KYFG_CameraClose(cameraHandle)
    (status,) = KYFG_Close(grabberHandle)
    assert error_count == 0
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

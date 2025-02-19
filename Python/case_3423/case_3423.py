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
    parser.add_argument('--encoderInverterValue',  default=0, type=int, help='Inverter value for encoder')
    parser.add_argument('--encoderPositionTrigger',  default=12, type=int, help='Encoder Position Trigger')

    return parser

def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)
############
# Classes
############
class AXUCallbackStruct:
    def __init__(self):
        self.callbackCount = 0
class StreamCallbackStruct:
    def __init__(self):
        self.callbackCount = 0

############
# Functions
############

def AUXCallbackFunc(streamHandle, userContext):
    callbackStruct = cast(userContext, py_object).value
    callbackStruct.callbackCount += 1
    # print('TRIGGER', callbackStruct.callbackCount)
def streamCallbackFunc(buffHandle, userContext):

    if buffHandle == 0:
        return
    userContext.callbackCount += 1
    # print("Frame", userContext.callbackCount)
    try:
        (status,) = KYFG_BufferToQueue(buffHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
    except:
        return
    return
def SourcesControl(grabberHandle, source: str, command: int):
    # source - Source of the encoder
    # command = Rising or falling (1, 0)
    assert command == 0 or command == 1, 'Wrong value of command'
    KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "UserOutputSelector", f"UserOutput{'0' if source == 'A' else '1'}")
    KYFG_SetGrabberValueBool(grabberHandle, "UserOutputValue", bool(command))
def fourStepsForward(grabberHandle):
    print("\nSteps forward")
    print("Current position: ", KYFG_GetGrabberValueInt(grabberHandle, "EncoderValue")[1])
    SourcesControl(grabberHandle, "A", 1)
    time.sleep(0.5)
    SourcesControl(grabberHandle, "B", 1)
    time.sleep(0.5)
    SourcesControl(grabberHandle, "A", 0)
    time.sleep(0.5)
    SourcesControl(grabberHandle, "B", 0)
    time.sleep(0.5)
    print("New position: ", KYFG_GetGrabberValueInt(grabberHandle, "EncoderValue")[1])
def fourStepsBackward(grabberHandle):
    print("\nSteps backward")
    print("Current position: ", KYFG_GetGrabberValueInt(grabberHandle, "EncoderValue")[1])
    SourcesControl(grabberHandle, "B", 1)
    time.sleep(0.5)
    SourcesControl(grabberHandle, "A", 1)
    time.sleep(0.5)
    SourcesControl(grabberHandle, "B", 0)
    time.sleep(0.5)
    SourcesControl(grabberHandle, "A", 0)
    time.sleep(0.5)
    print("New position: ", KYFG_GetGrabberValueInt(grabberHandle, "EncoderValue")[1], '\n')
def encoderSetting(grabberHandle, encoderInverterValue, EncoderPositionTrigger):
    KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "EncoderSelector", "Encoder0")
    KYFG_SetGrabberValueBool(grabberHandle, "EncoderInverter", encoderInverterValue)  # change after bug fixing
    KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "EncoderASource", "KY_TTL_0")
    KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "EncoderBSource", "KY_TTL_1")
    KYFG_SetGrabberValueInt(grabberHandle, "EncoderValue", 10)
    KYFG_SetGrabberValueInt(grabberHandle, "EncoderPositionTrigger", EncoderPositionTrigger)
    KYFG_SetGrabberValueFloat(grabberHandle, "EncoderFilter", 1.)
    KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "EncoderEventEnable", "Disable")  # change if it is needed
def sourceASetting(grabberHandle):
    KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "LineSelector", "KY_TTL_0")
    KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "LineMode", "Output")
    KYFG_SetGrabberValueBool(grabberHandle, "LineInverter", False)
    KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "LineSource", "KY_USER_OUT_0")
def sourceBSetting(grabberHandle):
    KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "LineSelector", "KY_TTL_1")
    KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "LineMode", "Output")
    KYFG_SetGrabberValueBool(grabberHandle, "LineInverter", False)
    KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "LineSource", "KY_USER_OUT_1")
def grabberCameraSetting(grabberHandle, cameraIndex: int):
    KYFG_SetGrabberValueInt(grabberHandle, "CameraSelector", cameraIndex)
    KYFG_SetGrabberValueInt(grabberHandle, "CxpConnectionSelector", cameraIndex)
    KYFG_SetGrabberValueEnum(grabberHandle, "CameraTriggerMode", 1)
    KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "CameraTriggerActivation", "AnyEdge")
    KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "CameraTriggerSource", "KY_ENCODER_0")
    KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "CameraTriggerEventEnable", "Enable")
    KYFG_SetGrabberValueInt(grabberHandle, "TriggerSentCount", 0)
def cameraSetting(cameraHandle, triggerMode: int):
    KYFG_SetCameraValueEnum(cameraHandle, "TriggerMode", triggerMode)
    KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "TriggerSource", "LinkTrigger0")
def chameleonSetting(cameraHandle, triggerMode: int):
    KYFG_SetCameraValueEnum(cameraHandle, "SimulationTriggerMode", triggerMode)
    KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "SimulationTriggerSource", "KY_CAM_TRIG")
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
    encoderInverterValue = bool(args['encoderInverterValue'])
    EncoderPositionTrigger = args['encoderPositionTrigger']
    error_count = 0
    (grabberHandle,) = KYFG_Open(device_index)
    (status, camList) = KYFG_UpdateCameraList(grabberHandle)
    assert len(camList) > 0, 'There is no cameras on this grabber'
    aux_callback_struct = AXUCallbackStruct()
    (status,) = KYFG_AuxDataCallbackRegister(grabberHandle,AUXCallbackFunc, py_object(aux_callback_struct))
    encoderSetting(grabberHandle, encoderInverterValue, EncoderPositionTrigger)
    sourceASetting(grabberHandle)
    sourceBSetting(grabberHandle)
    HWFound = True
    for cameraIndex in range(len(camList)):
        cameraHandle = camList[cameraIndex]
        (status, cameraInfo) = KYFG_CameraInfo2(cameraHandle)
        (status,) = KYFG_CameraOpen2(cameraHandle, None)
        print(f'\n\nCamera {cameraInfo.deviceModelName} open for test\n')
        try:
            if "Chameleon" in cameraInfo.deviceModelName:
                chameleonSetting(cameraHandle, 1)
            else:
                cameraSetting(cameraHandle, 1)
        except:
            print("There is no triggerMode on this camera")
            HWFound = False
            continue
        grabberCameraSetting(grabberHandle, cameraIndex)
        (status, streamHandle) = KYFG_StreamCreate(cameraHandle, 0)
        stream_struct = StreamCallbackStruct()
        (status,) = KYFG_StreamBufferCallbackRegister(streamHandle, streamCallbackFunc, stream_struct)
        buffers_array = [0 for i in range(16)]
        (status, payload_size, _, _) = KYFG_StreamGetInfo(streamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_PAYLOAD_SIZE)
        for iFrame in range(len(buffers_array)):
            (status, buffers_array[iFrame]) = KYFG_BufferAllocAndAnnounce(streamHandle, payload_size, 0)
        (status,) = KYFG_BufferQueueAll(streamHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_UNQUEUED, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
        (status,) = KYFG_CameraStart(cameraHandle, streamHandle, 0)
        time.sleep(1)
        print("\nPOSITION MODE")
        KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "EncoderOutputMode", "Position")
        fourStepsForward(grabberHandle)
        fourStepsBackward(grabberHandle)
        print("trigger sent:", KYFG_GetGrabberValueInt(grabberHandle, "TriggerSentCount")[1])
        print('FrameCount', KYFG_GetGrabberValueInt(grabberHandle, "RXFrameCounter")[1])
        print('DropFrameCount', KYFG_GetGrabberValueInt(grabberHandle, "DropFrameCounter")[1])
        print("AUX callback count:", aux_callback_struct.callbackCount, "stream callback count:",
              stream_struct.callbackCount)
        print("\nSTEPFORWARD MODE")
        KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "EncoderOutputMode", "Stepforward")
        fourStepsForward(grabberHandle)
        fourStepsBackward(grabberHandle)
        print("trigger sent:", KYFG_GetGrabberValueInt(grabberHandle, "TriggerSentCount")[1])
        print('FrameCount', KYFG_GetGrabberValueInt(grabberHandle, "RXFrameCounter")[1])
        print('DropFrameCount', KYFG_GetGrabberValueInt(grabberHandle, "DropFrameCounter")[1])
        print("AUX callback count:", aux_callback_struct.callbackCount, "stream callback count:",
              stream_struct.callbackCount)
        print("\nSTEPBACKWARD MODE")
        KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "EncoderOutputMode", "Stepbackward")
        fourStepsForward(grabberHandle)
        fourStepsBackward(grabberHandle)
        print("trigger sent:", KYFG_GetGrabberValueInt(grabberHandle, "TriggerSentCount")[1])
        print('FrameCount', KYFG_GetGrabberValueInt(grabberHandle, "RXFrameCounter")[1])
        print('DropFrameCount', KYFG_GetGrabberValueInt(grabberHandle, "DropFrameCounter")[1])
        print("AUX callback count:", aux_callback_struct.callbackCount, "stream callback count:",
              stream_struct.callbackCount)
        print("\nANYSTEP MODE")
        KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "EncoderOutputMode", "Anystep")
        fourStepsForward(grabberHandle)
        fourStepsBackward(grabberHandle)
        print("trigger sent:", KYFG_GetGrabberValueInt(grabberHandle, "TriggerSentCount")[1])
        print('FrameCount', KYFG_GetGrabberValueInt(grabberHandle, "RXFrameCounter")[1])
        print('DropFrameCount', KYFG_GetGrabberValueInt(grabberHandle, "DropFrameCounter")[1])
        print("AUX callback count:", aux_callback_struct.callbackCount, "stream callback count:", stream_struct.callbackCount)
        (status,) = KYFG_CameraStop(cameraHandle)
        if KYFG_GetGrabberValueInt(grabberHandle, "TriggerSentCount")[1]/2 != KYFG_GetGrabberValueInt(grabberHandle, "RXFrameCounter")[1]:
            error_count += 1
        KYFG_SetGrabberValueInt(grabberHandle, "CxpConnectionSelector", cameraIndex)
        KYFG_SetGrabberValueInt(grabberHandle, "TriggerSentCount", 0)

        if "Chameleon" in cameraInfo.deviceModelName:
            chameleonSetting(cameraHandle, 0)
        else:
            cameraSetting(cameraHandle, 0)
        (status,) = KYFG_StreamBufferCallbackUnregister(streamHandle,streamCallbackFunc)
        (status,) = KYFG_StreamDelete(streamHandle)
        (status,) = KYFG_CameraClose(cameraHandle)
    KYFG_GrabberExecuteCommand(grabberHandle, "EncoderReset")
    if KYFG_GetGrabberValueInt(grabberHandle, "EncoderValue")[1] != 0 or KYFG_GetGrabberValueInt(grabberHandle, "EncoderValueAtReset")[1] != 10:
        print('Reset function is not working correctly')
        error_count += 1
    if aux_callback_struct.callbackCount != 36 * len(camList):
        print(f'ERROR: AUXCallbackCount', aux_callback_struct.callbackCount)
    print("EncoderValue:", KYFG_GetGrabberValueInt(grabberHandle, "EncoderValue")[1])
    print("EncoderValueAtReset:", KYFG_GetGrabberValueInt(grabberHandle, "EncoderValueAtReset")[1])
    (status,) = KYFG_Close(grabberHandle)
    assert error_count == 0, 'Test not passed'
    if not HWFound:
        return CaseReturnCode.NO_HW_FOUND
    print(f'\nExiting from CaseRun({args}) with code SUCCESS...')
    return CaseReturnCode.SUCCESS


# The flow starts here
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

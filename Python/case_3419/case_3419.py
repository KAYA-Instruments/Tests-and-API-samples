# Default KAYA import
import sys
import os
import argparse
import time

sys.path.insert(0, os.environ['KAYA_VISION_POINT_PYTHON_PATH'])

from KYFGLib import *
from enum import IntEnum  # for CaseReturnCode


# Common Case imports

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
    parser.add_argument('--outputLine', default='KY_TTL_0', type=str, help='Output line')
    parser.add_argument('--inputLine', default='KY_TTL_2', type=str, help='input line')
    parser.add_argument('--expectedFPS', default=40, type=int, help='expectedFPS')
    parser.add_argument('--duration', default=10, type=int, help='Stream duration')

    return parser

def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)
############
# Classes
############
class StreamCallbackStruct:
    def __init__(self):
        self.callbackCounter = 0
############
# Functions
############
def streamCallbackFunction(buffHandle, userContext):
    if buffHandle == 0:
        return
    userContext.callbackCounter += 1
    try:
        (status,) = KYFG_BufferToQueue(buffHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
    except:
        return
def outputLineSetting(grabberHandle, outputLine):
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "LineSelector", f"{outputLine}")
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "LineMode", "Output")
    (status,) = KYFG_SetGrabberValueBool(grabberHandle, "LineInverter", False)
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "LineSource", "KY_TIMER_ACTIVE_0")
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "LineEventMode", "Disabled")
def inputLineSetting(grabberHandle, inputLine):
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "LineSelector", f"{inputLine}")
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "LineMode", "Input")
    (status,) = KYFG_SetGrabberValueBool(grabberHandle, "LineInverter", False)
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "LineSource", "KY_DISABLED")
    # (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "LineEventMode", "RisingEdge")
def timerSetting(grabberHandle, expectedPulseRate):
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "TimerSelector", "Timer0")
    timer_delay = timer_duration = 1e6 / expectedPulseRate / 2
    (status,) = KYFG_SetGrabberValueFloat(grabberHandle, "TimerDelay", timer_delay)
    (status,) = KYFG_SetGrabberValueFloat(grabberHandle, "TimerDuration", timer_duration)
    # (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "TimerActivation", "RisingEdge")
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "TimerTriggerSource", "KY_DISABLED")
def chameleonTriggerSet(cameraHandle, value: int):
    (status,) = KYFG_SetCameraValueEnum(cameraHandle, "SimulationTriggerMode", value)
    (status,) = KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "SimulationTriggerActivation", "RisingEdge")
    (status,) = KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "SimulationTriggerSource", "KY_CAM_TRIG")
def cameraTriggerSet(cameraHandle, value: int):
    (status,) = KYFG_SetCameraValueEnum(cameraHandle, "TriggerMode", value)
    (status,) = KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "TriggerActivation", "RisingEdge")
    (status,) = KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "TriggerSource", "LinkTrigger0")
def grabberCameraSetting(grabberHandle, cameraIndex, triggerSource):
    (status,) = KYFG_SetGrabberValueInt(grabberHandle, "CameraSelector", cameraIndex)
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "CameraTriggerMode", "On")
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "CameraTriggerActivation", "AnyEdge")
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "CameraTriggerSource", triggerSource)
    (status,) = KYFG_SetGrabberValueFloat(grabberHandle, "CameraTriggerFilter", 1.)
    # (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "CameraTriggerSource", "KY_TIMER_ACTIVE_0")


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
    
    # pushing arguments
    outputLine = args['outputLine']
    inputLine = args['inputLine']
    expectedFPS = args['expectedFPS']
    duration = args['duration']
    error_count = 0

    # opening grabber
    (grabberHandle,) = KYFG_Open(device_index)
    
    # looking for cameras
    (status, camList) = KYFG_UpdateCameraList(grabberHandle)
    print(f'Found {len(camList)} cameras')
    assert len(camList) > 0, 'There are no cameras on this grabber'
    
    outputLineSetting(grabberHandle, outputLine)
    inputLineSetting(grabberHandle, inputLine)
    timerSetting(grabberHandle, expectedFPS)
    for cameraIndex in range(len(camList)):
        cameraHandle = camList[cameraIndex]
        (status, camInfo) = KYFG_CameraInfo2(cameraHandle)
        (status,) = KYFG_CameraOpen2(cameraHandle, None)
        print(f'Camera {camInfo.deviceModelName} is opened for test')
        grabberCameraSetting(grabberHandle, cameraIndex, inputLine)
        if 'Chameleon' in camInfo.deviceModelName:
            chameleonTriggerSet(cameraHandle, 1)
        else:
            try:
                cameraTriggerSet(cameraHandle, 1)
            except Exception as e:
                print(f'{type(e)} {str(e)}')
                continue
        (status, streamHandle) = KYFG_StreamCreate(cameraHandle, 0)
        stream_callback_struct = StreamCallbackStruct()
        (status,) = KYFG_StreamBufferCallbackRegister(streamHandle, streamCallbackFunction, stream_callback_struct)
        buffers_array = [0 for i in range(16)]
        (status, payload_size, _, _) = KYFG_StreamGetInfo(streamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_PAYLOAD_SIZE)
        for iFrame in range(len(buffers_array)):
            (status, buffers_array[iFrame]) = KYFG_BufferAllocAndAnnounce(streamHandle, payload_size, 0)
        (status,) = KYFG_BufferQueueAll(streamHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_UNQUEUED, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
        (status,) = KYFG_CameraStart(cameraHandle, streamHandle, 0)
        time.sleep(1)
        (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "TimerTriggerSource", "KY_CONTINUOUS")
        time.sleep(duration)
        (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "TimerTriggerSource", "KY_DISABLED")
        (status,) = KYFG_CameraStop(cameraHandle)
        if 'Chameleon' in camInfo.deviceModelName:
            chameleonTriggerSet(cameraHandle, 0)
        else:
            cameraTriggerSet(cameraHandle, 0)
            
        # enable this selector only if you are using more than one camera
        # (status) = KYFG_SetGrabberValueInt(grabberHandle, "CxpConnectionSelector", cameraIndex)
        (status, trigger_sent) = KYFG_GetGrabberValueInt(grabberHandle, "TriggerSentCount")
        (status, TriggerMissedCount) = KYFG_GetGrabberValueInt(grabberHandle, "TriggerMissedCount")
        (status, TriggerAcknowledgeCount) = KYFG_GetGrabberValueInt(grabberHandle, "TriggerAcknowledgeCount")
        (status, TriggerChangeCount) = KYFG_GetGrabberValueInt(grabberHandle, "TriggerChangeCount")
        (status,) = KYFG_SetGrabberValueInt(grabberHandle, "TriggerSentCount", 0)
        (status,) = KYFG_SetGrabberValueInt(grabberHandle, "TriggerMissedCount", 0)
        (status,) = KYFG_SetGrabberValueInt(grabberHandle, "TriggerAcknowledgeCount", 0)
        (status,) = KYFG_SetGrabberValueInt(grabberHandle, "TriggerChangeCount", 0)
        (status,) = KYFG_StreamBufferCallbackUnregister(streamHandle, streamCallbackFunction)
        (status, frame_counter) = KYFG_GetGrabberValueInt(grabberHandle, "RXFrameCounter")
        (status, drop_frame_counter) = KYFG_GetGrabberValueInt(grabberHandle, "DropFrameCounter")
        (status,) = KYFG_StreamDelete(streamHandle)
        KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "CameraTriggerMode", "Off")
        (status,) = KYFG_CameraClose(cameraHandle)
        print("Camera test result:")
        print('trigger_sent', trigger_sent)
        print('TriggerMissedCount', TriggerMissedCount)
        print('TriggerAcknowledgeCount', TriggerAcknowledgeCount)
        print('TriggerChangeCount', TriggerChangeCount)
        print('frame_counter', frame_counter)
        print('drop_frame_counter', drop_frame_counter)
        print("CallbackCounter", stream_callback_struct.callbackCounter)
        if abs(frame_counter-(expectedFPS*duration)) > (expectedFPS*duration)/100:
            error_count += 1
    (status,) = KYFG_Close(grabberHandle)
    assert error_count == 0, "Test not Passed"
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

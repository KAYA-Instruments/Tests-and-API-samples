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
    parser.add_argument('--duration', type=int, default=10, help='Stream duration')
    return parser

def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)
##########
# Classes
##########
class CameraCallbacksCounter:
    def __init__(self):
        self.streamCallbackCounter = 0
        self.cameraCallbackCounter = 0
class GrabberCallbacksCounter:
    def __init__(self):
        self.auxCallbackCounter = 0
        self.eventCallbackCounter = 0
##########
# Functions
#########
def cameraCallbackFunction(userContext, streamHandle):
    streamInfo = cast(userContext, py_object).value
    streamInfo.cameraCallbackCounter += 1
def device_event_callback_func(userContext, event):
    # print(type(userContext))
    streamInfo = cast(userContext, py_object).value
    streamInfo.eventCallbackCounter += 1
def auxCallbackFunc(bufferHandle, userContext):
    streamInfo = cast(userContext, py_object).value
    streamInfo.auxCallbackCounter += 1
def streamCallbackFunction(buffHandle, userContext):
    if buffHandle == 0:
        return
    userContext.streamCallbackCounter += 1
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
    duration = args['duration']
    grabbers = [0 for i in range(infosize_test)]
    grabbers_info = [KY_DEVICE_INFO() for i in range(infosize_test)]
    grabber_callbacks = [0 for i in range(infosize_test)]
    camera_callbacks = [[0 for i in range(4)] for i in range(infosize_test)]
    camera_infos_array = [[KYFGCAMERA_INFO2() for i in range(4)] for i in range(infosize_test)]
    camerasArray = [[0 for i in range (4)] for i in range(infosize_test)]
    streamHandleArray = [[0 for i in range (4)] for i in range(infosize_test)]
    error_count = 0
    for x in range(0, infosize_test):
        (status, device_info) = KY_DeviceInfo(x)
        grabbers_info[x] = device_info
        if device_info.m_Flags == KY_DEVICE_INFO_FLAGS.GRABBER and not device_info.isVirtual:
            try:
                (grabberHandle,) = KYFG_Open(x)
                grabbers[x] = grabberHandle
                (status, camerasArray[x]) = KYFG_UpdateCameraList(grabberHandle)
            except:
                grabbers[x] = 0
                continue
        else:
            grabbers[x] = 0
    # Grabber preparation
    for i in range(len(grabbers)):
        if grabbers[i] == 0:
            continue
        grabberHandle = grabbers[i]
        print(f"\nGrabber: {hex(int(grabberHandle))}")
        (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "TimerSelector", "Timer0")
        (status,) = KYFG_SetGrabberValueFloat(grabberHandle, "TimerDelay", 50000.)
        (status,) = KYFG_SetGrabberValueFloat(grabberHandle, "TimerDuration", 50000.)
        (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "TimerActivation", "RisingEdge")
        (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "TimerTriggerSource", "KY_DISABLED")
        (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "TimerEventMode", "RisingEdge")
        # callbacks registration
        grabber_callbacks_counter = GrabberCallbacksCounter()
        (status,) = KYFG_AuxDataCallbackRegister(grabberHandle, auxCallbackFunc, py_object(grabber_callbacks_counter))
        print("AUX Callback registered")
        (status,) = KYDeviceEventCallBackRegister(grabberHandle, device_event_callback_func, py_object(grabber_callbacks_counter))
        print("Event Callback registered")
        grabber_callbacks[i] = grabber_callbacks_counter
        # camera preparation
        for camera_index in range(len(camerasArray[i])):
            cameraHandle = camerasArray[i][camera_index]
            (status, camera_infos_array[i][camera_index]) = KYFG_CameraInfo2(cameraHandle)
            if "Chameleon" in camera_infos_array[i][camera_index].deviceModelName:
                continue
            print(f'Camera: {hex(cameraHandle)} : {camera_infos_array[i][camera_index].deviceModelName}')
            (status,) = KYFG_CameraOpen2(cameraHandle, None)
            (status,) = KYFG_SetGrabberValueInt(grabberHandle, "CameraSelector", camera_index)
            (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "CameraTriggerMode", "On")
            (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "CameraTriggerActivation", "AnyEdge")
            (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "CameraTriggerSource", "KY_TIMER_ACTIVE_0")
            (status,) = KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "TriggerMode", "On")
            (status,) = KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "TriggerSource", "LinkTrigger0")
            # callbacks registration and stream start
            camera_callbacks_counter = CameraCallbacksCounter()
            (status,) = KYFG_CameraCallbackRegister(cameraHandle, cameraCallbackFunction, py_object(camera_callbacks_counter))
            print("Camera Callback registered")
            (status, streamHandle) = KYFG_StreamCreate(cameraHandle, 0)
            streamHandleArray[i][camera_index] = streamHandle
            (status,) = KYFG_StreamBufferCallbackRegister(streamHandle, streamCallbackFunction, camera_callbacks_counter)
            print("Stream Callback registered")
            camera_callbacks[i][camera_index] = camera_callbacks_counter
            (status,payload_size, _,_) = KYFG_StreamGetInfo(streamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_PAYLOAD_SIZE)
            number_of_buffers = [0 for i in range(16)]
            for iFrame in range(len(number_of_buffers)):
                (status, number_of_buffers[iFrame]) = KYFG_BufferAllocAndAnnounce(streamHandle, payload_size, 0)
            (status,) = KYFG_BufferQueueAll(streamHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_UNQUEUED,
                                            KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
            (status,) = KYFG_CameraStart(cameraHandle, streamHandle, 0)
    # Start trigger generation
    for i in range(len(grabbers)):
        if grabbers[i] == 0:
            continue
        KYFG_SetGrabberValueEnum_ByValueName(grabbers[i], "TimerTriggerSource", "KY_CONTINUOUS")
    time.sleep(duration)
    for i in range(len(grabbers)):
        if grabbers[i] == 0:
            continue
        (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabbers[i], "TimerTriggerSource", "KY_DISABLED")
    for i in range(len(grabbers)):
        if grabbers[i] == 0:
            continue
        grabberHandle = grabbers[i]
        print(f"\nClosing grabber {hex(grabberHandle.val)}")
        for camera_index in range(len(camerasArray[i])):
            cameraHandle = camerasArray[i][camera_index]
            (status,) = KYFG_CameraStop(cameraHandle)
            print(f'Camera {camera_infos_array[i][camera_index].deviceModelName} closed')
            (status,) = KYFG_SetGrabberValueInt(grabberHandle, "CameraSelector", camera_index)
            (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "CameraTriggerMode", "Off")
            (status,) = KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "TriggerMode", "Off")
            (status) = KYFG_CameraCallbackUnregister(cameraHandle, cameraCallbackFunction)
            (status) = KYFG_StreamBufferCallbackUnregister(streamHandleArray[i][camera_index],streamCallbackFunction)
            (status,) = KYFG_StreamDelete(streamHandleArray[i][camera_index])
            (status,) = KYFG_CameraClose(cameraHandle)
        (status,) = KYFG_AuxDataCallbackUnregister(grabberHandle, auxCallbackFunc)
        (status,) = KYDeviceEventCallBackUnregister(grabberHandle, device_event_callback_func)
        (status,) = KYFG_Close(grabberHandle)
        for i in range(len(grabbers)):
            if grabbers[i] == 0:
                continue
            print(f'\nGrabber: {grabbers_info[i].szDeviceDisplayName}: ')
            print("auxCallbackCounter", grabber_callbacks[i].auxCallbackCounter)
            print("eventCallbackCounter", grabber_callbacks[i].eventCallbackCounter)
            for camera_index in range(len(camerasArray[i])):
                if camerasArray[i][camera_index] == 0:
                    continue
                print(f'Camera: {camera_infos_array[i][camera_index].deviceModelName}')
                print("streamCallbackCounter", camera_callbacks[i][camera_index].streamCallbackCounter)
                print("cameraCallbackCounter", camera_callbacks[i][camera_index].cameraCallbackCounter)
                if camera_callbacks[i][camera_index].streamCallbackCounter == 0 \
                        or camera_callbacks[i][camera_index].cameraCallbackCounter == 0:
                    error_count += 1
            if grabber_callbacks[i].auxCallbackCounter == 0 or grabber_callbacks[i].eventCallbackCounter == 0:
                error_count += 1

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

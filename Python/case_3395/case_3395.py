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
    parser.add_argument('--secondGrabberIndex', default=2, type=int, help='Slave grabber ind')
    parser.add_argument('--streamDuration', default=100, type=int, help='Slave grabber ind')
    parser.add_argument('--expectedFPS', default=30, type=int, help='Slave grabber ind')
    return parser

def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)
##########
# Classes
##########
class StreamCallbackStruct():
    def __init__(self):
        self.callbackCounter = 0
        self.firstTimestamp = 0
        self.timestamps = []
##########
# Functions
#########

def streamCallbackFunc(buffHandle, userContext):
    if buffHandle == 0:
        print("BUFF Handle = 0")
        return
    # print('Frame')
    streamInfo = cast(userContext, py_object).value
    # print('Good callback streams buffer handle: ' + str(format(int(buffHandle), '02x')), end='\r')
    # userContext.callbackCounter += 1

    (KYFG_BufferGetInfo_status, pInfoTimestamp, pInfoSize, pInfoType) = KYFG_BufferGetInfo(
        buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_TIMESTAMP)  # UINT64
    if streamInfo.callbackCounter == 0:
        streamInfo.firstTimestamp = pInfoTimestamp
    streamInfo.timestamps.append(pInfoTimestamp-streamInfo.firstTimestamp)
    streamInfo.callbackCounter += 1
    # sys.stdout.flush()
    try:
        (KYFG_BufferToQueue_status,) = KYFG_BufferToQueue(buffHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
    except:
        return
    return
def camera_param_setter(cameraHandle):
    KYFG_SetCameraValueEnum(cameraHandle, "TriggerMode", 1)
    KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "TriggerSource", 'LinkTrigger0')
    # KYFG_SetCameraValueFloat(cameraHandle, "AcquisitionFrameRate", 10.00)
    KYFG_SetCameraValueFloat(cameraHandle, "ExposureTime", 5000.0)

def grabberCameraSetter(grabberHandle,cameraIndex):
    (status,) = KYFG_SetGrabberValueInt(int(grabberHandle), 'CameraSelector', cameraIndex)
    (status,) = KYFG_SetGrabberValueEnum(grabberHandle, "CameraTriggerMode", 1)
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, 'CameraTriggerActivation', "AnyEdge")
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, 'CameraTriggerSource', "KY_TTL_0")
def useLikeTriggerGenerator(masterGrabber, ExpectedFPS):
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(masterGrabber, 'LineSelector', "KY_TTL_0")
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(masterGrabber, 'LineMode', "Output")
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(masterGrabber, 'LineSource', "KY_TIMER_ACTIVE_0")
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(masterGrabber, 'TimerSelector', "Timer0")
    FrameTime = 1e+6 / ExpectedFPS
    (status,) = KYFG_SetGrabberValueFloat(int(masterGrabber), 'TimerDelay', FrameTime/2)
    (status,) = KYFG_SetGrabberValueFloat(int(masterGrabber), 'TimerDuration', FrameTime/2)
    (status,) = KYFG_SetGrabberValueEnum(masterGrabber, "TimerTriggerSource", 0)
def useLikeTriggerListener(masterGrabber):
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(masterGrabber, 'LineSelector', "KY_TTL_0")
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(masterGrabber, 'LineMode', "Input")
    KYFG_SetGrabberValueEnum(masterGrabber, "LineEventMode", 1)  # Delete after
    # (status,) = KYFG_SetGrabberValueEnum_ByValueName(masterGrabber, 'LineSource', "Disabled")
    (status,) = KYFG_SetGrabberValueEnum(masterGrabber, "LineSource", 0)
    KYFG_SetGrabberValueInt(int(masterGrabber), "TriggerChangeCount", 27707)  # For delete
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
    streamDuration = args['streamDuration']
    expectedFPS = args['expectedFPS']
    secondGrabberIndex = args['secondGrabberIndex']
    (grabber1,) = KYFG_Open(device_index)
    (grabber2,) = KYFG_Open(secondGrabberIndex)
    (status, grabber1CameraList) = KYFG_UpdateCameraList(grabber1)
    grabber1CameraList = grabber1CameraList[:1]
    (status, grabber2CameraList) = KYFG_UpdateCameraList(grabber2)
    grabber2CameraList = grabber2CameraList[:1]
    print('detected cameras', len(grabber1CameraList), len(grabber2CameraList))

    assert len(grabber1CameraList) != 0 or len(grabber2CameraList) != 0
    # grabber timestamps
    useLikeTriggerGenerator(grabber1, expectedFPS)

    for cameraHandle in grabber1CameraList:
        (status,) = KYFG_CameraOpen2(cameraHandle, None)
        (status, camInfo) = KYFG_CameraInfo2(cameraHandle)
        print(f'Camera {camInfo.deviceModelName} opened on first grabber')
        camera_param_setter(cameraHandle)
        grabberCameraSetter(grabber1, grabber1CameraList.index(cameraHandle))
        KYFG_SetGrabberValueInt(int(grabber1), "CameraSelector", 0)
    useLikeTriggerListener(grabber2)
    for cameraHandle in grabber2CameraList:
        (status,) = KYFG_CameraOpen2(cameraHandle, None)
        (status, camInfo) = KYFG_CameraInfo2(cameraHandle)
        print(f'Camera {camInfo.deviceModelName} opened on second grabber')
        camera_param_setter(cameraHandle)
        grabberCameraSetter(grabber2, grabber2CameraList.index(cameraHandle))
    masterCallbackStructList = []
    slaveCallbackStructList = []
    masterStreamHandleArray = []
    slaveStreamHandleArray = []
    # Master grabber stream prep
    for cameraHandle in grabber1CameraList[:1]:
        (status, camInfo) = KYFG_CameraInfo2(cameraHandle)
        (status, streamHandle) = KYFG_StreamCreate(cameraHandle, 0)
        masterStreamHandleArray.append(streamHandle)
        streamCallbackStruct = StreamCallbackStruct()
        masterCallbackStructList.append(streamCallbackStruct)
        (status,) = KYFG_StreamBufferCallbackRegister(streamHandle, streamCallbackFunc, py_object(streamCallbackStruct))
        (_, payload_size, _, _) = KYFG_StreamGetInfo(streamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_PAYLOAD_SIZE)
        (_, buf_allignment, _, _) = KYFG_StreamGetInfo(streamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_BUF_ALIGNMENT)
        streamBufferHandle = [0 for i in range(32)]
        for iFrame in range(len(streamBufferHandle)):
            (status, streamBufferHandle[iFrame]) = KYFG_BufferAllocAndAnnounce(streamHandle, payload_size, None)

        print(f'GrabberHandle: {grabber1}; CameraHandle: {hex(cameraHandle)}; streamHandle: {streamHandle}')
        print('Stram preparation completed')
        (status,) = KYFG_BufferQueueAll(streamHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_UNQUEUED,
                                        KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
        (status,) = KYFG_CameraStart(cameraHandle, streamHandle, 0)
        print(f"Camera {camInfo.deviceModelName} stream started")
        # Slave grabber stream prep
    for cameraHandle in grabber2CameraList:
        (status, camInfo) = KYFG_CameraInfo2(cameraHandle)
        (status, streamHandle) = KYFG_StreamCreate(cameraHandle, 0)
        slaveStreamHandleArray.append(streamHandle)
        streamCallbackStruct = StreamCallbackStruct()
        slaveCallbackStructList.append(streamCallbackStruct)
        (status,) = KYFG_StreamBufferCallbackRegister(streamHandle, streamCallbackFunc,
                                                      py_object(streamCallbackStruct))
        (_, payload_size, _, _) = KYFG_StreamGetInfo(streamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_PAYLOAD_SIZE)
        (_, buf_allignment, _, _) = KYFG_StreamGetInfo(streamHandle,
                                                       KY_STREAM_INFO_CMD.KY_STREAM_INFO_BUF_ALIGNMENT)
        streamBufferHandle = [0 for i in range(100)]
        for iFrame in range(len(streamBufferHandle)):
            (status, streamBufferHandle[iFrame]) = KYFG_BufferAllocAndAnnounce(streamHandle, payload_size, None)

        (status,) = KYFG_BufferQueueAll(streamHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_UNQUEUED,
                                        KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
        print(f'GrabberHandle: {grabber2}; CameraHandle: {hex(cameraHandle)}; streamHandle: {streamHandle}')
        print('Stram preparation completed')
        (status,) = KYFG_CameraStart(cameraHandle, streamHandle, 0)
        print(f"Camera {camInfo.deviceModelName} stream started")
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabber1, 'TimerSelector', "Timer0")
    (status,) = KYFG_SetGrabberValueEnum(grabber1, "TimerTriggerSource", 42)  # Continuous
    time.sleep(streamDuration)
    (status,) = KYFG_SetGrabberValueEnum(grabber1, "TimerTriggerSource", 0)
    for cameraHandle in grabber1CameraList:
        print('cameraHandle', cameraHandle)
        streamHandle = masterStreamHandleArray[grabber1CameraList.index(cameraHandle)]
        streamCallbackStruct = masterCallbackStructList[grabber1CameraList.index(cameraHandle)]
        (status, camInfo) = KYFG_CameraInfo2(cameraHandle)
        (status,) = KYFG_CameraStop(cameraHandle)
        (status,) = KYFG_StreamBufferCallbackUnregister(streamHandle, streamCallbackFunc)
        (status,) = KYFG_SetGrabberValueInt(int(grabber1), "CameraSelector", grabber1CameraList.index(cameraHandle))
        (status, frame_counter) = KYFG_GetGrabberValueInt(grabber1, "RXFrameCounter")
        (status, drop_frame_counter) = KYFG_GetGrabberValueInt(grabber1, "DropFrameCounter")
        (status,) = KYFG_StreamDelete(streamHandle)
        KYFG_SetCameraValueEnum(cameraHandle, "TriggerMode", 0)
        (status,) = KYFG_CameraClose(cameraHandle)
        print(f"Camera {camInfo.deviceModelName} Closed")
        print("frame_counter: ", frame_counter)
        print("drop_frame_counter: ", drop_frame_counter)
        print("callbackCounter: ", streamCallbackStruct.callbackCounter)
        KYFG_SetGrabberValueEnum(grabber1, "CameraTriggerMode", 0)
    for cameraHandle in grabber2CameraList:
        print('cameraHandle', cameraHandle)
        streamHandle = slaveStreamHandleArray[grabber2CameraList.index(cameraHandle)]
        streamCallbackStruct = slaveCallbackStructList[grabber2CameraList.index(cameraHandle)]
        (status, camInfo) = KYFG_CameraInfo2(cameraHandle)
        (status,) = KYFG_CameraStop(cameraHandle)
        (status,) = KYFG_StreamBufferCallbackUnregister(streamHandle, streamCallbackFunc)
        (status,) = KYFG_SetGrabberValueInt(int(grabber2), "CameraSelector", grabber2CameraList.index(cameraHandle))
        (status, frame_counter) = KYFG_GetGrabberValueInt(grabber2, "RXFrameCounter")
        (status, drop_frame_counter) = KYFG_GetGrabberValueInt(grabber2, "DropFrameCounter")
        (status,) = KYFG_StreamDelete(streamHandle)
        KYFG_SetCameraValueEnum(cameraHandle, "TriggerMode", 0)
        (status,) = KYFG_CameraClose(cameraHandle)
        print(f"Camera {camInfo.deviceModelName} Closed")
        print("frame_counter: ", frame_counter)
        print("drop_frame_counter: ", drop_frame_counter)
        print("callbackCounter: ", streamCallbackStruct.callbackCounter)
        KYFG_SetGrabberValueEnum(grabber2, "CameraTriggerMode", 0)
    differences = []
    print(f"N Master_timestamp; slave_timestamp; diff;instant_fps_1; instant_fps_2; aux_master; aux_slave; diff")
    for i in range(len(masterCallbackStructList[0].timestamps)):
        difference = masterCallbackStructList[0].timestamps[i] - slaveCallbackStructList[0].timestamps[i]
        differences.append(difference)
        if i > 0:
            print(f"{i + 1}: ", masterCallbackStructList[0].timestamps[i], slaveCallbackStructList[0].timestamps[i],
                  difference)
        else:
            print(f"{i+1}: ", masterCallbackStructList[0].timestamps[i], slaveCallbackStructList[0].timestamps[i],
                  difference)
    (status,) = KYFG_Close(int(grabber1))
    (status,) = KYFG_Close(int(grabber2))
    last_second_difference = differences[len(differences)-expectedFPS:]
    assert abs(sum(last_second_difference)/len(last_second_difference)) < 166000*expectedFPS,\
        'Test not passed: Difference between timestamps to large'
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

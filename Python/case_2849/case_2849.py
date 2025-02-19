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
                        help='Index of PCI device to use, run this script with "--deviceList" to see available devices')

    # Other arguments needed for this specific case, PARSE CASE SPECIFIC ARGUMENTS UNDER THIS LINE:
    parser.add_argument('--framesNumber', type=int, default=16, help='framesNumber')
    parser.add_argument('--acquisitionFrameRate', type=float, default=40.0, help='AcquisitionFrameRate')
    parser.add_argument('--segmentsPerBuffer', type=int, default=10, help='SegmentsPerBuffer')
    parser.add_argument('--duration', type=int, default=5,help='Duration one stream')

    return parser

def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)

class StreamInfoStruct:
    def __init__(self):
        self.width = 0
        self.height = 0
        self.callbackCount = 0
        return

def Stream_callback_func(buffHandle, userContext):

    if buffHandle == NULL_STREAM_BUFFER_HANDLE or buffHandle == INVALID_STREAM_BUFFER_HANDLE:
        Stream_callback_func.copyingDataFlag = 0
        return
    userContext.callbackCount += 1
    print('Good callback streams buffer handle: ' + str(format(int(buffHandle), '02x')), end='\r')


    print('buffer ' + str(buffHandle) + ': height=' + str(userContext.height) + ', width=' + str(
        userContext.width) + ', callback count=' + str(userContext.callbackCount))
    (status,)=KYFG_BufferToQueue(buffHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)

def waitForSleep(sleepTime):
    threadSleepSeconds = sleepTime
    print(f"Thread sleep for {threadSleepSeconds} seconds: ")
    for remaining in range(threadSleepSeconds, 0, -1):
        sys.stdout.write("\r")
        sys.stdout.write("{:2d} seconds remaining".format(remaining))
        sys.stdout.flush()
        time.sleep(1)
    sys.stdout.write("\rComplete!            \n")
    return threadSleepSeconds

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
    framesNumber = args["framesNumber"]
    acquisitionFrameRate = args["acquisitionFrameRate"]
    segmentsPerBuffer = args["segmentsPerBuffer"]
    duration=args['duration']
    assert acquisitionFrameRate*duration>framesNumber,f'Camera cannot sent {framesNumber} frames for {duration} seconds'
    (grabberHandle,)=KYFG_Open(device_index)
    (status,camera_list)=KYFG_UpdateCameraList(grabberHandle)
    assert len(camera_list)!=0, 'Thera is no cameras on this grabber'
    error_count=0
    for cameraHandle in camera_list:
        streamBufferHandle = [0 for i in range(framesNumber)]
        streamAllignedBuffer = [0 for i in range(framesNumber)]
        (status,)=KYFG_CameraOpen2(cameraHandle, None)
        try:
            if KYFG_IsGrabberValueImplemented(grabberHandle, 'TriggerMode'):
                KYFG_SetGrabberValueEnum(grabberHandle, "TriggerMode", 0)
            if KYFG_IsCameraValueImplemented(cameraHandle, "TriggerMode"):
                KYFG_SetCameraValueEnum(cameraHandle, "TriggerMode", 0)
        except:
            pass
        (status, cameraInfo)=KYFG_CameraInfo2(cameraHandle)
        print(f'{"*"*25}TEST FOR CAMERA {cameraInfo.deviceModelName}{"*"*25}')
        try:
            (status,)=KYFG_SetCameraValueFloat(cameraHandle, "AcquisitionFrameRate", acquisitionFrameRate)
        except:
            print(f'Parameter "AcquisitionFrameRate" {acquisitionFrameRate} for the camera {cameraInfo.deviceModelName} cannot be set .')
            error_count += 1
            continue
        (status,)=KYFG_SetGrabberValueInt(grabberHandle, "CameraSelector", camera_list.index(cameraHandle))
        (status,)=KYFG_SetGrabberValueInt(grabberHandle, "SegmentsPerBuffer", segmentsPerBuffer)
        (status,cameraStreamHandle)=KYFG_StreamCreate(cameraHandle, 0)
        streamInfoStruct = StreamInfoStruct()
        (KYFG_GetValue_status, width) = KYFG_GetCameraValueInt(cameraHandle, "Width")
        (KYFG_GetValue_status, height) = KYFG_GetCameraValueInt(cameraHandle, "Height")
        streamInfoStruct.width = width
        streamInfoStruct.height = height
        (status,) = KYFG_StreamBufferCallbackRegister(cameraStreamHandle, Stream_callback_func, streamInfoStruct)
        (KYFG_StreamGetInfo_status, payload_size, frameDataSize, pInfoType) = \
            KYFG_StreamGetInfo(cameraStreamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_PAYLOAD_SIZE)
        (KYFG_StreamGetInfo_status, buf_allignment, frameDataAligment, pInfoType) = \
            KYFG_StreamGetInfo(cameraStreamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_BUF_ALIGNMENT)
        for iFrame in range(len(streamBufferHandle)):
            streamAllignedBuffer[iFrame] = aligned_array(buf_allignment, c_ubyte, payload_size)
            (status, streamBufferHandle[iFrame]) = KYFG_BufferAnnounce(cameraStreamHandle,
                                                                       streamAllignedBuffer[iFrame], None)
        (KYFG_BufferQueueAll_status,) = KYFG_BufferQueueAll(cameraStreamHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_UNQUEUED,
                                                            KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
        (status,)=KYFG_CameraStart(cameraHandle,cameraStreamHandle, framesNumber)
        waitForSleep(duration)
        (status,)=KYFG_CameraStop(cameraHandle)
        (status,) = KYFG_StreamBufferCallbackUnregister(cameraStreamHandle, Stream_callback_func)
        (status,)=KYFG_StreamDelete(cameraStreamHandle)
        (status,)=KYFG_CameraClose(cameraHandle)
        print(f'RESULT\n\nCamera {cameraInfo.deviceModelName}\n callbacks: {streamInfoStruct.callbackCount}')
        if streamInfoStruct.callbackCount != framesNumber:
            print(f'Test is not pass for camera {cameraInfo.deviceModelName}')
            error_count+=1
    (status,)=KYFG_Close(grabberHandle)
    assert error_count==0, 'There is errors on cameras'
    print(f'\nExiting from CaseRun({args}) with code 0...')
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

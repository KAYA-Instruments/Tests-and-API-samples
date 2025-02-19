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
    parser.add_argument('--cameraModel', type=str, default='Iron250C', help='Model of camera')
    parser.add_argument('--test_time', type=int, default=5, help='Time of duration test')
    parser.add_argument('--allocated_buffers', type=int, default=10, help='Buffers for allocate')
    parser.add_argument('--width', type=int, default=1600, help='Width')
    parser.add_argument('--height', type=int, default=1600, help='Height')
    parser.add_argument('--acquisition_frame_rate', type=float, default=80.0, help='Acquisition frame rate')
    return parser

def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)
def waitForTestTime(time_for_sleep):
    threadSleepSeconds = time_for_sleep
    print(f"Thread sleep for {threadSleepSeconds} seconds: ")
    for remaining in range(threadSleepSeconds, 0, -1):
        sys.stdout.write("\r")
        sys.stdout.write("{:2d} seconds remaining".format(remaining))
        sys.stdout.flush()
        time.sleep(1)
    sys.stdout.write("\rComplete!            \n")
    return threadSleepSeconds

def is_approximately_equal(num1, num2, tolerance_percent):
    tolerance = tolerance_percent / 100.0
    diff = abs(num1 - num2)
    avg = (abs(num1) + abs(num2)) / 2.0
    return diff <= avg * tolerance
#####Callback registr

class StreamStruct:
    def __init__(self):
        self.callbackCounter=0
        self.timestamps=[]
def callback_func(bufferHandle,userContext):
    try:
        (status, pInfoBuffer, pInfoSize, pInfoType)=KYFG_BufferGetInfo(bufferHandle,
                                                                       KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_TIMESTAMP)
        userContext.callbackCounter += 1
        userContext.timestamps.append(pInfoBuffer)
        (KYFG_BufferToQueue_status,) = KYFG_BufferToQueue(bufferHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
    except:pass
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
    cameraModel=args['cameraModel']
    test_time=args['test_time']
    allocated_buffers=args['allocated_buffers']
    width=args['width']
    height=args['height']
    acquisition_frame_rate=args['acquisition_frame_rate']
    (grabber_handle,)=KYFG_Open(device_index)
    (status,camerasList)=KYFG_UpdateCameraList(grabber_handle)
    if len(camerasList)==0:
        print('There is no cameras on this Grabber')
        return CaseReturnCode.NO_HW_FOUND
    camera_list_for_test=[]
    for cameraHandle in camerasList:
        (status, cameraInfo)=KYFG_CameraInfo2(cameraHandle)
        if cameraModel in cameraInfo.deviceModelName or cameraModel in cameraInfo.deviceVendorName:
            camera_list_for_test.append(cameraHandle)
    print(f'Camera list fot test: {camera_list_for_test}')
    if len (camera_list_for_test)==0:
        return CaseReturnCode.NO_HW_FOUND
    if len(camerasList)==0:
        print('There is no cameras you need on this Grabber')
        return CaseReturnCode.NO_HW_FOUND
    for cameraHandle in camera_list_for_test:
        (status,)=KYFG_CameraOpen2(cameraHandle,None)
        try:
            if KYFG_IsGrabberValueImplemented(grabber_handle, 'TriggerMode'):
                KYFG_SetGrabberValueEnum(grabber_handle, "TriggerMode", 0)
            if KYFG_IsCameraValueImplemented(cameraHandle, "TriggerMode"):
                KYFG_SetCameraValueEnum(cameraHandle, "TriggerMode", 0)
            if KYFG_IsCameraValueImplemented(cameraHandle, "SimulationTriggerMode"):
                KYFG_SetCameraValueEnum(cameraHandle, "SimulationTriggerMode", 0)
        except:
            pass
        (status,camera_info)=KYFG_CameraInfo2(cameraHandle)
        print(f'Test for camera: {camera_info.deviceVendorName} {camera_info.deviceModelName}')
        #set camera value
        (status,)=KYFG_SetCameraValueInt(cameraHandle, "Width", width)
        (status,)=KYFG_SetCameraValueInt(cameraHandle, "Height", height)
        if KYFG_IsCameraValueImplemented(cameraHandle, 'AcquisitionFrameRate'):
            (status,)=KYFG_SetCameraValueFloat(cameraHandle, "AcquisitionFrameRate", acquisition_frame_rate)
        #stream_prearing
        (status,streamHandle)=KYFG_StreamCreate(cameraHandle,0)
        stream_struct=StreamStruct()
        (status,)=KYFG_StreamBufferCallbackRegister(streamHandle,callback_func,stream_struct)
        streamBuffersHandle = [0 for i in range(int(allocated_buffers))]
        (status, payload_size, frameDataSize, pInfoType) = \
            KYFG_StreamGetInfo(streamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_PAYLOAD_SIZE)
        for i in streamBuffersHandle:
            (status, streamBuffersHandle[i])=KYFG_BufferAllocAndAnnounce(streamHandle,payload_size,0)
        (status,)=KYFG_BufferQueueAll(streamHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_UNQUEUED, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
        (status,)=KYFG_CameraStart(cameraHandle,streamHandle, 0)
        waitForTestTime(test_time)
        (status,)=KYFG_CameraStop(cameraHandle)
        (status,)=KYFG_StreamBufferCallbackUnregister(streamHandle,callback_func)
        (status,) =KYFG_StreamDelete(streamHandle)
        (status,) =KYFG_CameraClose(cameraHandle)
        for i in range(1,len(stream_struct.timestamps)):
            print(f'Timestamp calculate FPS = {(1e9 / (stream_struct.timestamps[i] - stream_struct.timestamps[i - 1]))}')
            assert abs(1e9 / (stream_struct.timestamps[i] - stream_struct.timestamps[i - 1]))-acquisition_frame_rate < 1, \
                'Timestamp of frame and timestamp for FPS is not equals'

    (status,) =KYFG_Close(grabber_handle)

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
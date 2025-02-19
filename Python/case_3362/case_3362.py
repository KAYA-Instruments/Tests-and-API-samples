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
import psutil
import subprocess
import platform


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
    parser.add_argument('--numberOfTests', type=int, default=2, help='Number of test cycles')
    parser.add_argument('--numberOfBuffers', type=int, default=1000, help='Number of buffers for allocate')
    parser.add_argument('--instance', type=int,default=0, help='Instance')
    return parser


def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)


class StreamStruct:
    def __init__(self):
        self.callbackCount = 0
        return


def callbackFunction(buffHandle, userContext):
    if buffHandle == NULL_STREAM_BUFFER_HANDLE or buffHandle == INVALID_STREAM_BUFFER_HANDLE:
        return
    userContext.callbackCount += 1
    try:
        (KYFG_BufferToQueue_status,) = KYFG_BufferToQueue(buffHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
    except:
        return
    return


def is_approximately_equal(num1, num2, tolerance_percent):
    tolerance = tolerance_percent / 100.0
    diff = abs(num1 - num2)
    avg = (abs(num1) + abs(num2)) / 2.0
    return diff <= avg * tolerance


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
    RAM_before = psutil.virtual_memory()
    numberOfTests = args['numberOfTests']
    numberOfBuffers = args['numberOfBuffers']
    instance = args['instance']
    python_ver = 'python' if "Windows" in platform.platform() else "python3"
    error_count = 0
    if instance == 0:
        instance_process = subprocess.Popen(
            [python_ver, f"{__file__}", '--unattended', "--deviceIndex", f"{str(device_index)}", "--instance", "1",
             '--numberOfTests', str(numberOfTests), '--numberOfBuffers', str(numberOfBuffers)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        stdout, stderr = instance_process.communicate()
        print(stdout)
        print(stderr)
        time.sleep(10)
        RAM_after = psutil.virtual_memory()
        print(f'RAM_before: {RAM_before}')
        print(f'RAM_after: {RAM_after}')
        print(f'error_count: {error_count}')
        assert is_approximately_equal(RAM_before.free, RAM_after.free, 5) and instance_process.returncode == 0,\
            'Test not passed'



    else:
        for i in range(numberOfTests):
            current_pid = os.getpid()
            print(f'Iteration {i + 1}')
            process = psutil.Process(current_pid)
            memory_info_before = process.memory_info()
            print('RAM before start ITERATION', memory_info_before)
            (grabberHandle,) = KYFG_Open(device_index)
            (status, cameraList) = KYFG_UpdateCameraList(grabberHandle)
            assert len(cameraList)>0, 'Thera no cameras on this grabber'
            for cameraHandle in cameraList:
                (status, camInfo) = KYFG_CameraInfo2(cameraHandle)
                (status,) = KYFG_CameraOpen2(cameraHandle, None)
                print(f'Camera {camInfo.deviceModelName} is open')
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
                streamStruct = StreamStruct()
                (status,) = KYFG_StreamBufferCallbackRegister(streamHandle, callbackFunction, streamStruct)
                streamBufferHandle = [0 for i in range(numberOfBuffers)]
                streamAllignedBuffer = [0 for i in range(numberOfBuffers)]
                (status, payload_size, frameDataSize, pInfoType) = \
                    KYFG_StreamGetInfo(streamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_PAYLOAD_SIZE)

                (KYFG_StreamGetInfo_status, buf_allignment, frameDataAligment, pInfoType) = \
                    KYFG_StreamGetInfo(streamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_BUF_ALIGNMENT)

                # allocate memory for desired number of frame buffers
                for iFrame in range(len(streamBufferHandle)):
                    streamAllignedBuffer[iFrame] = aligned_array(buf_allignment, c_ubyte, payload_size)
                    # print("Address of alligned array: " + hex(addressof(streamAllignedBuffer[iFrame])))
                    (status, streamBufferHandle[iFrame]) = KYFG_BufferAnnounce(streamHandle,
                                                                               streamAllignedBuffer[iFrame], None)
                (status,) = KYFG_BufferQueueAll(streamHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_UNQUEUED,
                                                KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
                (status,) = KYFG_CameraStart(cameraHandle, streamHandle, 0)
                time.sleep(5)
                (status,) = KYFG_CameraStop(cameraHandle)
                (status, frameCounter) = KYFG_GetGrabberValueInt(grabberHandle, "RXFrameCounter")
                print(f'Results for camera {camInfo.deviceModelName}: ')
                print('frameCounter: ', frameCounter, '\nCallbackCounter: ', streamStruct.callbackCount)
                if frameCounter == 0 or streamStruct.callbackCount == 0:
                    print("Acquisition is not started")
                    error_count += 1
                (status,) = KYFG_StreamBufferCallbackUnregister(streamHandle, callbackFunction)
                (status,) = KYFG_StreamDelete(streamHandle)
                (status,) = KYFG_CameraClose(cameraHandle)
            (status,) = KYFG_Close(grabberHandle)
            process = psutil.Process(current_pid)
            memory_info_after = process.memory_info()
            print('RAM after end ITERATION', memory_info_after)
            print(f'error_count = {error_count}')
            assert error_count == 0

            assert abs(memory_info_before.rss-memory_info_after.rss) < memory_info_before/100*5, "Test not passed"


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

# Default KAYA import
import sys
import os
import argparse
import time

sys.path.insert(0, os.environ['KAYA_VISION_POINT_PYTHON_PATH'])

from KYFGLib import *
from enum import IntEnum # for CaseReturnCode

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
    parser.add_argument('--number_of_frames', default=10, type=int, help='Number of received frames')
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
class CameraParameters:
    def __init__(self, name):
        if "Chameleon" in name:
            self.triggerMode_param_name = "SimulationTriggerMode"
            self.triggerMode_value_on = "Triggered"
            self.triggerMode_value_off = "FreeRun"
            self.triggerActivation_param_name = "SimulationTriggerActivation"
            self.triggerActivation_value = "RisingEdge"
            self.triggerSource_param_name = "SimulationTriggerSource"
            self.triggerSource_value = "KY_CAM_TRIG"
        if "Iron" in name:
            self.triggerMode_param_name = "TriggerMode"
            self.triggerMode_value_on = "On"
            self.triggerMode_value_off = "Off"
            self.triggerActivation_param_name = "TriggerActivation"
            self.triggerActivation_value = "RisingEdge"
            self.triggerSource_param_name = "TriggerSource"
            self.triggerSource_value = "LinkTrigger0"
############
# Functions
############
def streamCallbackFunc(buffHandle, userContext):
    if buffHandle == NULL_STREAM_BUFFER_HANDLE or buffHandle == INVALID_STREAM_BUFFER_HANDLE:
        return
    # print('Good callback streams buffer handle: ' + str(format(int(buffHandle), '02x')), end='\r')
    userContext.callbackCounter += 1
    sys.stdout.flush()
    (KYFG_BufferToQueue_status,) = KYFG_BufferToQueue(buffHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
    return
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
    number_of_frames = args['number_of_frames']
    (grabberHandle,) = KYFG_Open(device_index)
    error_count = 0
    # Frame grabber GPIO trigger
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "LineSelector", "KY_TTL_0")
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "LineMode", "Output")
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "LineSource", "KY_USER_OUT_0")
    (status,) = KYFG_SetGrabberValueBool(grabberHandle, "UserOutputValue", False)
    (status, cameraList) = KYFG_UpdateCameraList(grabberHandle)
    assert len(cameraList) > 0, "There are no cameras on this grabber"
    for cameraHandle in cameraList:
        (status, camInfo) = KYFG_CameraInfo2(cameraHandle)
        camera = CameraParameters(camInfo.deviceModelName)
        (status,) = KYFG_CameraOpen2(cameraHandle, None)
        print(f'Camera {camInfo.deviceModelName} is open')
        (status,) = KYFG_SetGrabberValueInt(grabberHandle, "CameraSelector", cameraList.index(cameraHandle))
        (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "CameraTriggerMode", "On")
        (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "CameraTriggerActivation", "AnyEdge")
        (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "CameraTriggerSource", "KY_TTL_0")
        # Set camera parameters
        (status,) = KYFG_SetCameraValueEnum_ByValueName(cameraHandle, camera.triggerMode_param_name,
                                                        camera.triggerMode_value_on)
        (status,) = KYFG_SetCameraValueEnum_ByValueName(cameraHandle, camera.triggerActivation_param_name,
                                                        camera.triggerActivation_value)
        (status,) = KYFG_SetCameraValueEnum_ByValueName(cameraHandle, camera.triggerSource_param_name,
                                                        camera.triggerSource_value)
        (status, streamHandle) = KYFG_StreamCreate(cameraHandle, 0)
        streamCallbackStruct = StreamCallbackStruct()
        (status,) = KYFG_StreamBufferCallbackRegister(streamHandle, streamCallbackFunc, streamCallbackStruct)
        (_, payload_size, _, _) = KYFG_StreamGetInfo(streamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_PAYLOAD_SIZE)
        (_, buf_allignment, _, _) = KYFG_StreamGetInfo(streamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_BUF_ALIGNMENT)
        streamBufferHandle = [0 for i in range(16)]
        streamAllignedBuffer = [0 for i in range(16)]
        for iFrame in range(len(streamBufferHandle)):
            streamAllignedBuffer[iFrame] = aligned_array(buf_allignment, c_ubyte, payload_size)
            (status, streamBufferHandle[iFrame]) = KYFG_BufferAnnounce(streamHandle, streamAllignedBuffer[iFrame], None)
        (status,) = KYFG_BufferQueueAll(streamHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_UNQUEUED,
                                        KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
        (status,) = KYFG_CameraStart(cameraHandle, streamHandle, 0)
        # print(KYFG_GetGrabberValueBool(grabberHandle, "UserOutputValue"))
        time.sleep(1)
        for i in range(number_of_frames):
            (status,) = KYFG_SetGrabberValueBool(grabberHandle, "UserOutputValue", True)
            # print(KYFG_GetGrabberValueBool(grabberHandle, "UserOutputValue"))
            time.sleep(1)
            (status,) = KYFG_SetGrabberValueBool(grabberHandle, "UserOutputValue", False)
            time.sleep(1)
        (status,) = KYFG_CameraStop(cameraHandle)
        (status, frame_counter) = KYFG_GetGrabberValueInt(grabberHandle, "RXFrameCounter")
        (status, drop_frame_counter) = KYFG_GetGrabberValueInt(grabberHandle, "DropPacketCounter")
        (status,) = KYFG_StreamBufferCallbackUnregister(streamHandle, streamCallbackFunc)
        (status,) = KYFG_StreamDelete(streamHandle)
        (status,) = KYFG_SetCameraValueEnum_ByValueName(cameraHandle, camera.triggerMode_param_name,
                                                        camera.triggerMode_value_off)
        (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "CameraTriggerMode", "Off")
        (status,) = KYFG_CameraClose(cameraHandle)
        print("frame_counter: ", frame_counter)
        print("drop_frame_counter: ", drop_frame_counter)
        print("callbackCounter: ", streamCallbackStruct.callbackCounter)
        if frame_counter != number_of_frames != streamCallbackStruct.callbackCounter or drop_frame_counter > 0:
            error_count += 1
    (status,) = KYFG_Close(grabberHandle)
    assert error_count == 0, "Test not passed"
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

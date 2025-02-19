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
import xml.etree.ElementTree as ET
import time
from zipfile import ZipFile


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
    parser.add_argument('--number_of_cycles', type=int, default=1000, help='Number of Cycles')
    parser.add_argument('--cameraModel', type=str,default='Iron255C', help='Camera model')

    return parser


camHandleArray = {}
cameras_info_before_streaming = {}


class StreamStructure:
    def __init__(self) -> None:
        self.is_assertion_exist = False
        self.callbackCount = 0
        self.cameraHandle = 0


def Stream_callback_func(buffHandle, userContext):
    global cameras_info_before_streaming
    if buffHandle == 0:
        return

    try:
        (KYFG_BufferToQueue_status,) = KYFG_BufferToQueue(buffHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
    except KYException as err:
        print(f"KYException: {err}")
        return

    (KYFG_BufferGetInfo_status, pInfoID, pInfoSize, pInfoType) = KYFG_BufferGetInfo(
        buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_STREAM_HANDLE)  # UINT32
    print(f"StreamHandle: {hex(pInfoID)}")
    (_, camInfo) = KYFG_CameraInfo2(userContext.cameraHandle)
    cam_before_streaming = cameras_info_before_streaming[pInfoID]

    if not userContext.is_assertion_exist:
        userContext.is_assertion_exist = (
                cam_before_streaming['device_vendor_name'] != camInfo.deviceVendorName
                or
                cam_before_streaming['device_model_name'] != camInfo.deviceModelName
        )
    userContext.callbackCount += 1


def check_is_camera_available(deviceModelName, camHandles):
    cams_num = len(camHandles)
    for i in range(cams_num):
        cameraHandle = camHandles[i]
        (Status, camInfo) = KYFG_CameraInfo2(cameraHandle)
        print(deviceModelName, camInfo.deviceModelName)
        if camInfo.deviceModelName in deviceModelName:
            return True
    return False


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

    number_of_cycles = args['number_of_cycles']
    cameraModel = args['cameraModel']
    streamBufferHandle = {}
    frames_count = 1000
    global cameras_info_before_streaming

    (grabberHandle,) = KYFG_Open(device_index)
    (status, camHandleArray[device_index]) = KYFG_UpdateCameraList(grabberHandle)

    cameras_length = len(camHandleArray[device_index])
    print("cameras_length", cameras_length)

    if not check_is_camera_available(cameraModel, camHandleArray[device_index]):
        KYFG_Close(grabberHandle)
        print(f"\nRequired camera {cameraModel} not found")
        return CaseReturnCode.NO_HW_FOUND

    stream_handle = {}
    Stream_callback_func.assertion_exist = False

    # Open all cameras
    for i in range(cameras_length):
        cameraHandle = camHandleArray[device_index][i]
        (status,) = KYFG_CameraOpen2(cameraHandle, None)
        try:
            if KYFG_IsGrabberValueImplemented(grabberHandle, 'TriggerMode'):
                KYFG_SetGrabberValueEnum(grabberHandle, "TriggerMode", 0)
            if KYFG_IsCameraValueImplemented(cameraHandle, "TriggerMode"):
                KYFG_SetCameraValueEnum(cameraHandle, "TriggerMode", 0)
        except:
            pass
        KYFG_SetCameraValueInt(cameraHandle, "Width", 1024)
        KYFG_SetCameraValueInt(cameraHandle, "Height", 512)

        (_, pixel_format_int, pixel_format_name) = KYFG_GetCameraValue(cameraHandle, "PixelFormat")


        if pixel_format_name.startswith("Mono"):
            setting_pixel_format = "Mono8"
        elif pixel_format_name.startswith('BayerBG'):
            setting_pixel_format = "BayerBG8"
        elif pixel_format_name.startswith('BayerGR'):
            setting_pixel_format = "BayerGR8"
        elif pixel_format_name.startswith('BayerRG'):
            setting_pixel_format = "BayerRG8"
        elif pixel_format_name.startswith('BayerGB'):
            setting_pixel_format = "BayerGB8"
        elif pixel_format_name.startswith('RGBA'):
            setting_pixel_format = "RGBA8"
        elif pixel_format_name.startswith('RGB'):
            setting_pixel_format = "RGB8"
        else:
            print(f"\nCamera does not support 8 bit pixelFormat. Current pixelFormat is: {pixel_format_name}")
            return CaseReturnCode.NO_HW_FOUND

        (SetCameraValueEnum_ByValueName_status,) = KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "PixelFormat",
                                                                                       setting_pixel_format)

        (_, max_frame_rate) = KYFG_GetCameraValueFloat(cameraHandle, "AcquisitionFrameRateMax")
        frame_rate = 1000.00 if max_frame_rate >= 1000 else max_frame_rate
        (camval_status,) = KYFG_SetCameraValueFloat(cameraHandle, "AcquisitionFrameRate", frame_rate)

    # Start acquisition
    for i in range(cameras_length):
        cameraHandle = camHandleArray[device_index][i]
        # create stream
        (status, stream_handle[i]) = KYFG_StreamCreate(cameraHandle, i)

        stream_structure = StreamStructure()
        stream_structure.cameraHandle = cameraHandle
        (KYFG_StreamBufferCallbackRegister_status,) = KYFG_StreamBufferCallbackRegister(stream_handle[i],
                                                                                        Stream_callback_func,
                                                                                        stream_structure)

        (_, device_vendor_name) = KYFG_GetCameraValueStringCopy(cameraHandle, 'DeviceVendorName')
        (_, device_model_name) = KYFG_GetCameraValueStringCopy(cameraHandle, 'DeviceModelName')
        cameras_info_before_streaming[int(stream_handle[i])] = {"device_vendor_name": device_vendor_name, "device_model_name": device_model_name}

        (status, payload_size, frameDataSize, pInfoType) = KYFG_StreamGetInfo(stream_handle[i], KY_STREAM_INFO_CMD.KY_STREAM_INFO_PAYLOAD_SIZE)
        
        streamBufferHandle[i] = {}
        for iFrame in range(0, frames_count):
            (KYFG_BufferAllocAndAnnounce_status, streamBufferHandle[i][iFrame]) = KYFG_BufferAllocAndAnnounce(stream_handle[i], payload_size, 0)
                        
        (KYFG_BufferQueueAll_status,) = KYFG_BufferQueueAll(
            stream_handle[i],
            KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_UNQUEUED,
            KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT
        )
        
        (KYFG_CameraStart_status,) = KYFG_CameraStart(cameraHandle, stream_handle[i], frames_count)
        
        counter = 0
        while stream_structure.callbackCount <= number_of_cycles and counter < number_of_cycles:
            time.sleep(0.1)
            counter += 1

        if stream_structure.is_assertion_exist:
            (CameraStop_status,) = KYFG_CameraStop(cameraHandle)
            KYFG_StreamBufferCallbackUnregister(stream_handle[i], Stream_callback_func)
            KYFG_StreamDelete(stream_handle[i])
            assert stream_structure.is_assertion_exist == False, 'DeviceVendorName or DeviceModelName does not match'
        else:
            (CameraStop_status,) = KYFG_CameraStop(cameraHandle)
            KYFG_StreamBufferCallbackUnregister(stream_handle[i], Stream_callback_func)
            KYFG_StreamDelete(stream_handle[i])

            (status, crc_errors) = KYFG_GetGrabberValue(cameraHandle, "CRCErrorCounter")
            assert crc_errors == 0, f"CRCErrorCounter:{crc_errors}"
            (status, dropped_packets) = KYFG_GetGrabberValue(cameraHandle, "DropPacketCounter")
            assert dropped_packets == 0, f"DropPacketCounter:{dropped_packets}"
            (status, dropped_frames) = KYFG_GetGrabberValue(cameraHandle, "DropFrameCounter")
            assert dropped_frames == 0, f"DropFrameCounter:{dropped_frames}"

    KYFG_Close(grabberHandle)
    print(f'\nExiting from CaseRun({args}) with code 0...')
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
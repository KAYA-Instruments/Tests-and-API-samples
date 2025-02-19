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
    parser.add_argument("--camera_model", type=str, default="Chameleon", help="Camera model")
    return parser

def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)
###################### Callback Function ####################################
class StreamInfoStruct:
    def __init__(self):
        self.width = 0
        self.height = 0
        self.callbackCount = 0
        return

def Stream_callback_func(buffHandle, userContext):
    try:
        (KYFG_BufferToQueue_status,) = KYFG_BufferToQueue(buffHandle ,KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
    except KYException:
        return
    Stream_callback_func.copyingDataFlag = 0
    return
################################################
def FindResolutionStep(camera_handle, min, param):
    step_list = [2, 4, 8, 16, 32]
    step: int
    real_step = 0
    for step in step_list:
        sum = min + step
        try:
            (status,) = KYFG_SetCameraValueInt(camera_handle, param, sum)
            real_step+=1
        except KYException:
            real_step = step
            continue
    return real_step
Stream_callback_func.data = 0
Stream_callback_func.copyingDataFlag = 0

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
    camera_model = args['camera_model']
    streamInfoStruct = StreamInfoStruct()
    streamBufferHandle = [0 for i in range(16)]
    streamAllignedBuffer = [0 for i in range(16)]
    #OPEN device
    (device_handle,) = KYFG_Open(device_index)
    device_info = device_infos[device_index]
    print(
        f'Opened device [{device_index}]: (PCI {device_info.nBus}:{device_info.nSlot}:{device_info.nFunction})"{device_info.szDeviceDisplayName}"')
    #scan and open camera
    (status, camHandleArray_col) = KYFG_UpdateCameraList(device_handle)
    print(f'Camera scan result:\nStatus: {status}\nCamHandleArray: {camHandleArray_col}')
    if len(camHandleArray_col) == 0:
        print('There is no cameras on this device')
        return CaseReturnCode.NO_HW_FOUND
    error_count=0

    camHandle = None


    for cameraHandle in camHandleArray_col:
        (status,camInfo) = KYFG_CameraInfo(cameraHandle)
        if camera_model in camInfo.deviceModelName:
            print(f'Camera {camInfo.deviceModelName} Found on grabber')
            camHandle = cameraHandle
            break
    if camHandle is None:
        print(f"Camera {camera_model} is not found on this grabber")
        return CaseReturnCode.NO_HW_FOUND
    (status,) = KYFG_CameraOpen2(camHandle, None)
    # check trigger mode
    try:
        if KYFG_IsGrabberValueImplemented(device_handle, 'TriggerMode'):
            KYFG_SetGrabberValueEnum(device_handle, "TriggerMode", 0)
        if KYFG_IsCameraValueImplemented(camHandle, "TriggerMode"):
            KYFG_SetCameraValueEnum(camHandle, "TriggerMode", 0)
        if KYFG_IsCameraValueImplemented(camHandle, "SimulationTriggerMode"):
            KYFG_SetCameraValueEnum(camHandle, "SimulationTriggerMode", 0)
    except:
        pass
    # (status, max_width ) = KYFG_GetCameraValueInt(camHandle, "WidthMax")
    # (status, max_height) = KYFG_GetCameraValueInt(camHandle, "HeightMax")
    # (status,min_width) = KYFG_GetCameraValueInt(camHandle, 'WidthMin')
    # (status, min_height) = KYFG_GetCameraValueInt(camHandle, 'HeightMin')
    (status, max_width, min_width) = KYFG_GetCameraValueIntMaxMin(camHandle, "Width")
    (status, max_height, min_height) = KYFG_GetCameraValueIntMaxMin(camHandle, "Height")

    width_step = FindResolutionStep(camHandle, min_width, "Width")
    height_step = FindResolutionStep(camHandle, min_height, "Height")
    for i in range(0, 5):
        width = int((int((max_width - min_width) / 4) * i) / width_step) * width_step + min_width
        height = int((int((max_height - min_height) / 4) * i) / height_step) * height_step + min_height
        streamInfoStruct.width = width
        streamInfoStruct.height = height
        try:
            (status,) = KYFG_SetCameraValueInt(camHandle, "Width", width)
            (status,) = KYFG_SetCameraValueInt(camHandle, "Height", height)
        except:continue
        print(f"Camera resolution is {width}x{height}")
        #stream register
        (KYFG_StreamCreate_status, cameraStreamHandle) = KYFG_StreamCreate(camHandle, 0)
        (KYFG_StreamBufferCallbackRegister_status,) = KYFG_StreamBufferCallbackRegister(cameraStreamHandle,
                                                                                        Stream_callback_func,
                                                                                        py_object(streamInfoStruct))
        #stream info
        (KYFG_StreamGetInfo_status, payload_size, frameDataSize, pInfoType) = \
            KYFG_StreamGetInfo(cameraStreamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_PAYLOAD_SIZE)

        (KYFG_StreamGetInfo_status, buf_allignment, frameDataAligment, pInfoType) = \
            KYFG_StreamGetInfo(cameraStreamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_BUF_ALIGNMENT)
        for iFrame in range(len(streamBufferHandle)):
            # streamAllignedBuffer[iFrame] = aligned_array(buf_allignment, c_ubyte, payload_size)
            (status, streamBufferHandle[iFrame]) = KYFG_BufferAllocAndAnnounce(cameraStreamHandle, payload_size, None)
        for iFrame in range(len(streamBufferHandle)):
            # (status, FPS) = KYFG_GetCameraValue(camera_handle, "AcquisitionFrameRate")
            # The low frame rate select for DropFrames check
            FPS = 4.0
            (status,) = KYFG_SetCameraValueFloat(camHandle, "AcquisitionFrameRate", FPS)

            (KYFG_BufferQueueAll_status,) = KYFG_BufferQueueAll(cameraStreamHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_UNQUEUED,
                                                                KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
            (KYFG_CameraStart_status,) = KYFG_CameraStart(camHandle, cameraStreamHandle, 0)
            time_s = int(iFrame / FPS + 1)
            time.sleep(time_s + 1)
            (CameraStop_status,) = KYFG_CameraStop(camHandle)

            # Ensure acquiring started and frames were acquired
            (status_rxf, fg_stat_rxf) = KYFG_GetGrabberValue(camHandle, "RXFrameCounter")
            (status_rxp, fg_stat_rxp) = KYFG_GetGrabberValue(camHandle, "RXPacketCounter")
            if fg_stat_rxp < fg_stat_rxf:
                print("RXFrameCounter < RXPacketCounter")
                error_count+=1
            (status, crc_errors) = KYFG_GetGrabberValue(camHandle, "CRCErrorCounter")
            (status, dropped_packets) = KYFG_GetGrabberValue(camHandle, "DropPacketCounter")
            (status, dropped_frames) = KYFG_GetGrabberValue(camHandle, "DropFrameCounter")
            print(f'CRCErrorCounter: {crc_errors}',f'DropPacketCounter: {dropped_packets}', f'DropFrameCounter: {dropped_frames}')
            print(f'RXFrameCounter: {fg_stat_rxf}', f'RXPacketCounter: {fg_stat_rxp}')
            print("Dropped frames: " + str(dropped_frames))
            print("Received frames: " + str(fg_stat_rxf))
            # Currently we have some DropFrames that we allow
            if 0 != dropped_frames or dropped_packets!=0 or crc_errors!=0:
                print('Not all "CRCErrorCounter", "DropPacketCounter", "DropFrameCounter" = 0')
                error_count+=1
            if fg_stat_rxf>fg_stat_rxp:
                print('fg_stat_rxf>fg_stat_rxp')
                error_count += 1
        (CallbackRegister_status,) = KYFG_StreamBufferCallbackUnregister(cameraStreamHandle, Stream_callback_func)
        (status,) = KYFG_StreamDelete(cameraStreamHandle)
    if (camHandle > 0):
        (KYFG_CameraClose_status,) = KYFG_CameraClose(camHandle)

    if (device_handle != 0):
        (KYFG_Close_status,) = KYFG_Close(device_handle)
    assert error_count==0, 'There are errors while test'
    return CaseReturnCode.SUCCESS



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

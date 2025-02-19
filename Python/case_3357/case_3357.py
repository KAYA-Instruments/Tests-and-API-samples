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
import pathlib


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
    return parser

def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)
######## globalVar
gTestCaseResults = {}

####### Classes
class StreamInfoStruct:
    def __init__(self):
        self.callbackCount = 0
        self.bufferData = None

####### CallbackFunc
def Stream_callback_func(buffHandle, userContext):
    if (buffHandle == 0 ):
        return
    userContext.callbackCount += 1
    (KYFG_BufferGetInfo_status, pInfoBase, pInfoSize, pInfoType) = KYFG_BufferGetInfo(
        buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_BASE)
    (KYFG_BufferGetInfo_status, buffer_size, pInfoSize, pInfoType) = KYFG_BufferGetInfo(
        buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_SIZE)
    buffContent = ctypes.string_at(pInfoBase, size=buffer_size)
    userContext.bufferData = buffContent
    try:
        (KYFG_BufferToQueue_status,) = KYFG_BufferToQueue(buffHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
    except: return

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

    global gTestCaseResults
    # Extract zip data
    raw_data_folder = pathlib.Path(__file__).parent
    # open grabber and find Chameleon
    (grabberHandle,) = KYFG_Open(device_index)
    (status, cameraList) = KYFG_UpdateCameraList(grabberHandle)
    cameraHandle = 0
    for cam in cameraList:
        (status, camInfo) = KYFG_CameraInfo2(cam)
        if 'Chameleon' in camInfo.deviceModelName:
            cameraHandle = cam
    if cameraHandle == 0:
        print('There is no Chameleon on this grabber')
        return CaseReturnCode.NO_HW_FOUND
    (status,) = KYFG_CameraOpen2(cameraHandle, None)
    # Set camera value
    (status,) = KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "SimulationTriggerMode", "FreeRun")
    (status,) = KYFG_SetCameraValueInt(cameraHandle, "Width", 512)
    (status,) = KYFG_SetCameraValueInt(cameraHandle, "Height", 512)
    (status,) = KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "VideoSourceType", "File")
    (status,) = KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "VideoSourceFileType", "Raw")
    for next_raw_data in raw_data_folder.iterdir():
        if not next_raw_data.name.endswith('.raw'):
            continue
        # Get expected  raw data
        with open(next_raw_data, mode="rb") as file:expected_raw = file.read()
        # Set camera value for stream
        pixel_format = next_raw_data.name.replace('.raw', '')
        (status,) = KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "PixelFormat", pixel_format)
        (status,) = KYFG_SetCameraValueString(cameraHandle, "SourceFilePath", str(next_raw_data))
        (status, path_value) = KYFG_GetCameraValueStringCopy(cameraHandle, "SourceFilePath")
        if path_value != str(next_raw_data):
            print(f'Setting path error for {pixel_format}:\n Required path: {next_raw_data}\nReal path: {path_value}')
            gTestCaseResults[pixel_format] = {'Status': 'Failed', 'Reason': 'Setting path error'}
            continue
        # Stream prepare
        (status, stream_handle) = KYFG_StreamCreate(cameraHandle, 0)
        stream_info_struct = StreamInfoStruct()
        (status,) = KYFG_StreamBufferCallbackRegister(stream_handle,Stream_callback_func,stream_info_struct)
        (KYFG_StreamGetInfo_status, payload_size, frameDataSize, pInfoType) = \
            KYFG_StreamGetInfo(stream_handle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_PAYLOAD_SIZE)
        (KYFG_StreamGetInfo_status, buf_allignment, frameDataAligment, pInfoType) = \
            KYFG_StreamGetInfo(stream_handle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_BUF_ALIGNMENT)
        # allocate memory for desired number of frame buffers
        streamBufferHandle = [0 for i in range(16)]
        streamAllignedBuffer = [0 for i in range(16)]
        for iFrame in range(len(streamBufferHandle)):
            streamAllignedBuffer[iFrame] = aligned_array(buf_allignment, c_ubyte, payload_size)
            (status, streamBufferHandle[iFrame]) = KYFG_BufferAnnounce(stream_handle, streamAllignedBuffer[iFrame], None)
        (status,) = KYFG_BufferQueueAll(stream_handle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_UNQUEUED,
                                                            KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
        (status,) = KYFG_CameraStart(cameraHandle, stream_handle, 1)
        time.sleep(1)
        (status,) = KYFG_CameraStop(cameraHandle)
        # Save compare result in dict
        if stream_info_struct.bufferData == expected_raw:
                gTestCaseResults[pixel_format] = {'Status': "Passed"}
        else:
            gTestCaseResults[pixel_format] = {'Status': "Failed", 'Reason': "Raw data from buffer not equals to expected"}
        (status,) = KYFG_StreamBufferCallbackUnregister(stream_handle, Stream_callback_func)
        (status,) = KYFG_StreamDelete(stream_handle)
    (status,) = KYFG_CameraClose(cameraHandle)
    (status,) = KYFG_Close(grabberHandle)
    for format, value in gTestCaseResults.items():
        print(format, value)
    for format, value in gTestCaseResults.items():
        assert value['Status'] == 'Passed', 'Test not passed'
    print(f'\nExiting from CaseRun({args}) with code 0...')
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
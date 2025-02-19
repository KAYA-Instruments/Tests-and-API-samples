# Common KAYA imports DO NOT EDIT!!!
import sys
import os
import argparse
sys.path.insert(0, os.environ['KAYA_VISION_POINT_PYTHON_PATH'])
from KYFGLib import *

# Common Case imports DO NOT EDIT!!!
from enum import IntEnum  # for CaseReturnCode

# additional imports required by particular case, ADD CASE SPECIFIC IMPORTS UNDER THIS LINE:
from datetime import datetime
import time
import threading
import subprocess


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
    parser.add_argument('--cameraIndex', type=int, default=0, help='Camera index for this instance')
    parser.add_argument('--number_of_sent_tests', type=int, default=3, help='Number of sent triggers')
    return parser

def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)

class StreamInfoStruct:
    def __init__(self):
        self.callbackCount = 0
        self.instantsFps = []
        self.timestamps = []
        return

def Stream_callback_func(buffHandle, userContext):

    if buffHandle == 0:
        return
    userContext.callbackCount += 1
    (KYFG_BufferGetInfo_status, pInfoFPS, pInfoSize, pInfoType) = KYFG_BufferGetInfo(
        buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_INSTANTFPS)
    (KYFG_BufferGetInfo_status, timestamp, pInfoSize, pInfoType) = KYFG_BufferGetInfo(
        buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_TIMESTAMP)

    userContext.instantsFps.append(pInfoFPS)
    userContext.timestamps.append(timestamp)

    try: (status,) = KYFG_BufferToQueue(buffHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
    except: return
    return

def is_approximately_equal(num1, num2, tolerance_percent):
    tolerance = tolerance_percent / 100.0
    diff = abs(num1 - num2)
    avg = (abs(num1) + abs(num2)) / 2.0
    return diff <= avg * tolerance

def waitFortime(time_for_sleep):
    threadSleepSeconds = time_for_sleep
    print(f"Thread sleep for {threadSleepSeconds} seconds: ")
    for remaining in range(threadSleepSeconds, 0, -1):
        sys.stdout.write("\r")
        sys.stdout.write("{:2d} seconds remaining".format(remaining))
        sys.stdout.flush()
        time.sleep(1)
    sys.stdout.write("\rComplete!            \n")
    return threadSleepSeconds
errorCount=0

def new_instance(device_index, camera_index, number_of_sent_tests):
    global errorCount
    instance_process = subprocess.Popen(
        ["python3", f"{__file__}", '--unattended', '--deviceIndex', f'{device_index}', "--cameraIndex", f"{camera_index}",
         "--number_of_sent_tests", f"{number_of_sent_tests}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        close_fds=True)

    stdout_output, stderr_output = instance_process.communicate()
    print(stdout_output.decode())
    print(stderr_output)
    return_code = instance_process.returncode
    print(return_code)
    if return_code!=0:
        errorCount+=1

    return return_code

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
    camera_index = args['cameraIndex']
    number_of_sent_tests = args['number_of_sent_tests']
    # if camera_index == 0:

    (grabber_handle,) = KYFG_Open(device_index)
    # try:
    #     (status, isSharingSupported) = KYFG_GetGrabberValueInt(grabber_handle, 'SWCapable_InterProcessSharing_Imp')
    #     if not isSharingSupported:
    #         print('Grabber sharing is not supported on this device')
    #         (status,) = KYFG_Close(grabber_handle)
    #         return CaseReturnCode.COULD_NOT_RUN
    # except:
    #     print('Grabber sharing is not supported on this device')
    #     (status,) = KYFG_Close(grabberHandle)
    #     return CaseReturnCode.COULD_NOT_RUN
    (status, camera_list,) = KYFG_UpdateCameraList(grabber_handle)
    for cam in camera_list:
        (status,camInfo)=KYFG_CameraInfo2(cam)
        if 'Chameleon' in camInfo.deviceModelName:
            camera_list.remove(cam)
            print(f'Camera {camInfo.deviceModelName} removed from camera list for test')
    if camera_index == 0:
        if len(camera_list) == 0:
            return CaseReturnCode.NO_HW_FOUND

    # Detect camera
    cameraHandle = camera_list[camera_index]
    if camera_index==0:
        (status,) = KYFG_CameraOpen2(camera_list[0], None)
    else:
        (status,) = KYFG_CameraOpen2(cameraHandle, None)

    (status, camera_info) = KYFG_CameraInfo2(cameraHandle)
    camera_master_link = camera_info.master_link
    # Select the "CxpConnectionSelector" where camera is connected (i.e master link of the camera)
    (status, camera_width_type) = KYFG_GetCameraValueType(cameraHandle, "Width")
    (status, camera_pixelFormat_type) = KYFG_GetCameraValueType(cameraHandle, "PixelFormat")
    (status, camera_binningSelector_type) = KYFG_GetCameraValueType(cameraHandle, "BinningSelector")
    (status, grabber_deviceStatus_type) = KYFG_GetGrabberValueType(grabber_handle, "DeviceStatus")
    (status, grabber_coreTemperature_type) = KYFG_GetGrabberValueType(grabber_handle, "DeviceTemperature")
    (status, debayer_mode) = KYFG_GetGrabberValueEnum(grabber_handle, "DebayerMode")
    (status, grabberpfName) = KYFG_GetGrabberValueStringCopy(grabber_handle, "PixelFormat")
    (status, camerapfName) = KYFG_GetCameraValueStringCopy(cameraHandle, "PixelFormat")

    # CxpRemoteTransferMaxRetries
    (status, grabber_IMax, grabber_IMin) = KYFG_GetGrabberValueIntMaxMin(grabber_handle, "Width")
    (status, grabber_FMax, grabber_FMin) = KYFG_GetGrabberValueFloatMaxMin(grabber_handle, "AcquisitionFps")
    (status, camera_IMax, camera_IMin) = KYFG_GetCameraValueIntMaxMin(cameraHandle, "Width")
    (status, camera_FMax, camera_FMin) = KYFG_GetCameraValueFloatMaxMin(cameraHandle, "AcquisitionFrameRate")
    #(status, camera_PropertyValue) = KY_GetCameraPropertyParameterValue(cameraHandle, "WidthMin", "ToolTip")
    #(status, grabber_PropertyValue) = KY_GetGrabberPropertyParameterValue(grabber_handle, "Width", "ToolTip")

    print(f"debayer_mode {debayer_mode}")
    assert (debayer_mode == 0) or (debayer_mode == 1), "Incorrect DebayerMode is returned"
    print(f"grabberpfName {grabberpfName}")
    assert (grabberpfName == "Normal") or ("Mono" in grabberpfName) or ("RGB" in grabberpfName) or ("Bayer" in grabberpfName), "Incorrect grabber PixelFormat is returned"
    print(f"camerapfName {camerapfName}")
    assert ("Mono" in camerapfName) or ("RGB" in camerapfName) or ("Bayer" in camerapfName), "Incorrect camera PixelFormat is returned"

    print(f'camera_width type {KY_CAM_PROPERTY_TYPE.PROPERTY_TYPE_INT == camera_width_type}')
    assert (KY_CAM_PROPERTY_TYPE.PROPERTY_TYPE_INT == camera_width_type), "Incorrect camera property type INT is returned"
    print(f'camera_pixelFormat type {KY_CAM_PROPERTY_TYPE.PROPERTY_TYPE_ENUM == camera_pixelFormat_type}')
    assert (KY_CAM_PROPERTY_TYPE.PROPERTY_TYPE_ENUM == camera_pixelFormat_type), "Incorrect camera property type ENUM is returned"
    print(f'camera_binningSelector type {KY_CAM_PROPERTY_TYPE.PROPERTY_TYPE_ENUM == camera_binningSelector_type}')
    assert (KY_CAM_PROPERTY_TYPE.PROPERTY_TYPE_ENUM == camera_binningSelector_type), "Incorrect camera property type ENUM is returned"
    print(f'grabber_deviceStatus_type {KY_CAM_PROPERTY_TYPE.PROPERTY_TYPE_STRING == grabber_deviceStatus_type}')
    assert (
                KY_CAM_PROPERTY_TYPE.PROPERTY_TYPE_STRING == grabber_deviceStatus_type), "Incorrect grabber property type STRING is returned"
    print(f'grabber_coreTemperature_type {KY_CAM_PROPERTY_TYPE.PROPERTY_TYPE_INT == grabber_coreTemperature_type}')
    assert (
            KY_CAM_PROPERTY_TYPE.PROPERTY_TYPE_INT == grabber_coreTemperature_type), "Incorrect grabber property type INT is returned"

    print(f'grabber_IMaxMin {grabber_IMax} {grabber_IMin}')
    assert (grabber_IMax > grabber_IMin), "Incorrect grabber IntMaxMin value is returned"
    print(f'grabber_FMaxMin {grabber_FMax} {grabber_FMin}')
    assert (grabber_FMax > grabber_FMin), "Incorrect grabber FloatMaxMin value is returned"
    print(f'camera_IMaxMin {camera_IMax} {camera_IMin}')
    assert (camera_IMax > camera_IMin), "Incorrect camera IntMaxMin value is returned"
    print(f'camera_FMaxMin {camera_FMax} {camera_FMin}')
    assert (camera_FMax > camera_FMin), "Incorrect camera FloatMaxMin value is returned"
    #print(f'camera_PropertyValue - {camera_PropertyValue}')
    #print(f'grabber_PropertyValue - {grabber_PropertyValue}')

    (status, streamHandle) = KYFG_StreamCreate(cameraHandle, 0)
    streamStruct = StreamInfoStruct()
    (status,) = KYFG_StreamBufferCallbackRegister(streamHandle, Stream_callback_func, streamStruct)
    # Retrieve information about required frame buffer size and alignment
    number_of_buffers = 16
    streamAlignedBuffer = {}
    streamBufferHandle = {}
    (KYFG_StreamGetInfo_status, payload_size, frameDataSize, pInfoType) = \
        KYFG_StreamGetInfo(streamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_PAYLOAD_SIZE)

    (KYFG_StreamGetInfo_status, buf_allignment, frameDataAlignment, pInfoType) = \
        KYFG_StreamGetInfo(streamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_BUF_ALIGNMENT)

    for iFrame in range(number_of_buffers):
        streamAlignedBuffer[iFrame] = aligned_array(buf_allignment, c_ubyte, payload_size)
        # print("Address of alligned array: " + hex(addressof(streamAllignedBuffer[iFrame])))
        (status, streamBufferHandle[iFrame]) = KYFG_BufferAnnounce(streamHandle,
                                                                   streamAlignedBuffer[iFrame], None)
    (status,) = KYFG_BufferQueueAll(streamHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_UNQUEUED,
                                    KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
    (status,) = KYFG_CameraStart(cameraHandle, streamHandle, 0)
    time.sleep(10)
    (status, frame_index) = KYFG_StreamGetFrameIndex(streamHandle)
    (status,) = KYFG_CameraStop(cameraHandle)

    print(f"Frame index: {frame_index}")
    assert (frame_index > 0), "Incorrect index of the last acquired frame"

    (status,) = KYFG_CameraClose(cameraHandle)
    (status,) = KYFG_Close(grabber_handle)

    print(f'\nExiting from CaseRun({args}) with code 0...')
    return CaseReturnCode.SUCCESS
if __name__ == "__main__":
    try:
        args_ = ParseArgs()
        return_code = CaseRun(args_)
        print(f'Case return code: {return_code}')
    except Exception as ex:
        print(f"Exception of type {type(ex)} occurred: {str(ex)}")
        exit(-200)

    exit(return_code)


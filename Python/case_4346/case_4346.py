# Common KAYA imports DO NOT EDIT!!!
import sys
import os
import argparse
sys.path.insert(0, os.environ['KAYA_VISION_POINT_PYTHON_PATH'])
from KYFGLib import *

# Common Case imports DO NOT EDIT!!!
from enum import IntEnum  # for CaseReturnCode

# additional imports required by particular case, ADD CASE SPECIFIC IMPORTS UNDER THIS LINE:
import shutil
import time
import random
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
    parser.add_argument("--number_of_frames", type=int, default=100,
                        help='Number of allocated frames and images for generation')
    parser.add_argument("--width", type=int, default=320, help="Image Width")
    parser.add_argument("--height", type=int, default=284, help='Image height')
    parser.add_argument("--bitDepth", type=int, default=16, help="Image bit depth")
    parser.add_argument("--frameRate", type=int, default=1100, help="Image bit depth")
    parser.add_argument("--ConnectionConfig", type=str, default="x1_CXP_2", help="Connection Config value")

    return parser


class StreamStruct:
    def __init__(self):
        self.callbackCounter = 0
        self.maxCallbackCounter = 0
        self.runStream = False

class ImageDescriptor:
    def __init__(self):
        self.width = 0
        self.height = 0
        self.folderPath = ''
        self.pixelFormat = ""

def streamCallbackFunc(bufferHandle, userContext):
    if bufferHandle == INVALID_STREAM_BUFFER_HANDLE:
        return
    userContext.callbackCounter += 1
    if userContext.callbackCounter >= userContext.maxCallbackCounter:
        userContext.runStream = False
    print(f"userContext.callbackCounter: {userContext.callbackCounter}", end='\r')
    try:
        (status,) = KYFG_BufferToQueue(bufferHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
    except:
        pass

def generateImage(imageDescriptor: ImageDescriptor, number_of_images: int ):
    bitDepth = 8 if imageDescriptor.pixelFormat.endswith("8") else 16
    for i in range(number_of_images):
        pixels_array = []
        number_of_bytes = int(imageDescriptor.width*imageDescriptor.height)
        [pixels_array.append(random.randint(0, 1 << bitDepth-1).to_bytes(2, byteorder='big', signed=False)) for next_byte in range(number_of_bytes)]
        with open(pathlib.Path(imageDescriptor.folderPath).joinpath(f"image_{i}.raw"), 'wb') as f:
            for b in pixels_array:
                f.write(b)


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
    images_folder = pathlib.Path(__file__).parent.joinpath("images_folder")
    imageDescriptor = ImageDescriptor()
    imageDescriptor.width = args["width"]
    number_of_frames = args["number_of_frames"]
    imageDescriptor.height = args["height"]
    frameRate = args['frameRate']
    connectionConfig = args["ConnectionConfig"]
    bitDepth = args["bitDepth"]
    if bitDepth not in range(8, 17, 2):
        print("Wrong parameter valaue: bitDepth")
        return CaseReturnCode.WRONG_PARAM_VALUE
    imageDescriptor.pixelFormat = f"Mono{bitDepth}"
    imageDescriptor.folderPath = images_folder.absolute().as_posix()
    if images_folder.exists():
        shutil.rmtree(images_folder)
    images_folder.mkdir()
    generateImage(imageDescriptor, number_of_frames)
    (grabberHandle,) = KYFG_Open(device_index)
    (status, camList) = KYFG_UpdateCameraList(grabberHandle)
    cameraHandle = None
    for cam in camList:
        (status, camInfo) = KYFG_CameraInfo2(cam)
        if "Chameleon" in camInfo.deviceModelName:
            cameraHandle = cam
            break
    if cameraHandle is None:
        print("There is no Chameleon camera on this grabber")
        return CaseReturnCode.NO_HW_FOUND
    (status,) = KYFG_CameraOpen2(cameraHandle, None)
    (status, camInfo) = KYFG_CameraInfo2(cameraHandle)
    print(camInfo.deviceModelName, "is open for test")
    try:
        if KYFG_IsGrabberValueImplemented(grabberHandle, 'TriggerMode'):
            KYFG_SetGrabberValueEnum(grabberHandle, "TriggerMode", 0)
        if KYFG_IsCameraValueImplemented(cameraHandle, "SimulationTriggerMode"):
            KYFG_SetCameraValueEnum(cameraHandle, "SimulationTriggerMode", 1)
            KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "SimulationTriggerSource", "KY_CAM_TRIG")
    except:
        pass
    KYFG_SetCameraValueInt(cameraHandle, "Width", imageDescriptor.width)
    KYFG_SetCameraValueInt(cameraHandle, "Height", imageDescriptor.height)
    KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "PixelFormat", imageDescriptor.pixelFormat)
    KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "VideoSourceType", "Folder")
    KYFG_SetCameraValueString(cameraHandle, "SourceFolderPath", imageDescriptor.folderPath)
    KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "ConnectionConfig", connectionConfig)
    # timer control
    KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "TimerSelector", "Timer0")
    KYFG_SetGrabberValueFloat(grabberHandle, "TimerDelay", float(1e6/frameRate/2))
    KYFG_SetGrabberValueFloat(grabberHandle, "TimerDuration", float(1e6/frameRate/2))
    KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "TimerActivation", "RisingEdge")
    KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "TimerTriggerSource", "KY_DISABLED")
    (status,) = KYFG_SetGrabberValueInt(grabberHandle, "CameraSelector", camList.index(cameraHandle))
    KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "CameraTriggerMode", "On")
    KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "CameraTriggerActivation", "AnyEdge")
    KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "CameraTriggerSource", "KY_TIMER_ACTIVE_0")


    streamStruct = StreamStruct()
    streamStruct.maxCallbackCounter = number_of_frames+2

    (status, streamHandle) = KYFG_StreamCreate(cameraHandle,0)
    buffers = [0 for i in range(16)]
    (status, payloadSize, _, _) = KYFG_StreamGetInfo(streamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_PAYLOAD_SIZE)
    for IFrame in buffers:
        (status, buffers[IFrame]) = KYFG_BufferAllocAndAnnounce(streamHandle, payloadSize, 0)
    (status,) = KYFG_StreamBufferCallbackRegister(streamHandle, streamCallbackFunc, streamStruct)
    (status,) = KYFG_BufferQueueAll(streamHandle,KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_UNQUEUED, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
    (status,) = KYFG_CameraStart(cameraHandle, streamHandle, 0)
    streamStruct.runStream = True
    KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "TimerTriggerSource", "KY_CONTINUOUS")
    # time.sleep(2)
    # if streamStruct.callbackCounter == 0:
    #     print("Acquisition is NOT STARTED")

    while streamStruct.runStream == True:
        if streamStruct.runStream == False:
            break
    KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "TimerTriggerSource", "KY_DISABLED")
    print("STOP")
    time.sleep(10)
    (status,) = KYFG_CameraStop(cameraHandle)
    KYFG_SetCameraValueEnum(cameraHandle, "SimulationTriggerMode", 0)
    (status, frameCounter) = KYFG_GetGrabberValueInt(grabberHandle, "RXFrameCounter")
    (status, dropFrameCounter) = KYFG_GetGrabberValueInt(grabberHandle, "DropFrameCounter")

    (status,) = KYFG_StreamBufferCallbackUnregister(streamHandle, streamCallbackFunc)
    (status,) = KYFG_StreamDelete(streamHandle)
    (status,) = KYFG_CameraClose(cameraHandle)
    (status,) = KYFG_Close(grabberHandle)
    shutil.rmtree(imageDescriptor.folderPath)
    print(f"\nTEST Statistic: \n\nFrame counter: {frameCounter}\nDrop frame counter: {dropFrameCounter}\n")
    assert frameCounter > number_of_frames and dropFrameCounter == 0, "Test not passed"
    print(f'\nExiting from CaseRun({args}) with code SUCCESS...')

    return CaseReturnCode.SUCCESS


def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)


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

# Common KAYA imports DO NOT EDIT!!!
import sys
import os
import argparse
sys.path.insert(0, os.environ['KAYA_VISION_POINT_PYTHON_PATH'])
from KYFGLib import *

# Common Case imports DO NOT EDIT!!!
from enum import IntEnum  # for CaseReturnCode

# additional imports required by particular case, ADD CASE SPECIFIC IMPORTS UNDER THIS LINE:
import random
import time

###################### Defines ####################################
frame_array = []
the_buffer = -1
counter = 0


def Stream_callback_func(buffHandle, userContext):
    global frame_array
    global the_buffer
    global counter
    if buffHandle == 0:
        return
    print('Good callback streams buffer handle: ' + str(buffHandle), end='\r')
    frame_array.append(buffHandle)
    counter += 1
    try:
        (KYFG_BufferToQueue_status,) = KYFG_BufferToQueue(buffHandle,KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
    except KYException:
        return

    (KYFG_BufferGetInfo_status, pInfoID, pInfoSize, pInfoType) = KYFG_BufferGetInfo(
        buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_ID)  # UINT32
    print(pInfoID, "counter = ", counter)
    assert the_buffer != pInfoID, "Buffer not revoked!!!"

    return

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
    parser.add_argument('--num_of_frames', type=int, default=100)
    parser.add_argument('--num_of_buffers', type=int, default=10)

    return parser


################################## Main #################################################################








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

    num_of_frames = args["num_of_frames"]
    num_of_buffers = args["num_of_buffers"]
    streamBufferHandle = [0 for i in range(num_of_buffers)]
    global the_buffer

    # open grabber
    (grabber_handle,) = KYFG_Open(device_index)
    print("Good connection to device " + str(device_index) + ", handle= " + str(grabber_handle))
    # detection camera
    (CameraScan_status, camHandleArray) = KYFG_UpdateCameraList(grabber_handle)
    if len(camHandleArray) == 0:
        return CaseReturnCode.NO_HW_FOUND
    camera_handle = camHandleArray[0]
    (status, cam_info) = KYFG_CameraInfo2(camera_handle)
    print(f"Automated select camera 0 {cam_info.deviceVendorName}")
    # open camera
    (status,) = KYFG_CameraOpen2(camHandleArray[0], None)
    # check trigger mode
    try:
        if KYFG_IsGrabberValueImplemented(grabber_handle, 'TriggerMode'):
            KYFG_SetGrabberValueEnum(grabber_handle, "TriggerMode", 0)
        if KYFG_IsCameraValueImplemented(camera_handle, "TriggerMode"):
            KYFG_SetCameraValueEnum(camera_handle, "TriggerMode", 0)
        if KYFG_IsCameraValueImplemented(camera_handle, "SimulationTriggerMode"):
            KYFG_SetCameraValueEnum(camera_handle, "SimulationTriggerMode", 0)
    except:
        pass
    print(f'Camera was connected successfully with handle {camera_handle}')

    # create stream
    (status, stream_handle) = KYFG_StreamCreate(camera_handle, 0)
    (KYFG_StreamBufferCallbackRegister_status,) = KYFG_StreamBufferCallbackRegister(stream_handle,
                                                                                    Stream_callback_func, 0)

    (status, payload_size, frameDataSize, pInfoType) = \
        KYFG_StreamGetInfo(stream_handle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_PAYLOAD_SIZE)

    for buffer in range(num_of_buffers):
        (status, streamBufferHandle[buffer]) = KYFG_BufferAllocAndAnnounce(stream_handle, payload_size, 0)

    the_buffer = random.randint(0, num_of_buffers - 1)
    print('the_buffer = ' + str(the_buffer))
    (status,) = KYFG_BufferRevoke(stream_handle, streamBufferHandle[the_buffer])

    (status,) = KYFG_BufferQueueAll(stream_handle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_UNQUEUED,
                            KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)

    (KYFG_CameraStart_status,) = KYFG_CameraStart(camera_handle, stream_handle, 0)

    # while True:
    #     if len(frame_array) >= num_of_frames:# or counter > 20:
    #         break
    #     time.sleep(0.2)
    time.sleep(10)

    (CameraStop_status,) = KYFG_CameraStop(camera_handle)
    print("Camera stopped")

    assert streamBufferHandle[the_buffer] not in frame_array, "Buffer not revoked"
    print("Buffer is revoked")

    (CallbackRegister_status,) = KYFG_StreamBufferCallbackUnregister(stream_handle, Stream_callback_func)
    print("Buffer unregistered")

    (status,) = KYFG_StreamDelete(stream_handle)
    print("Stream deleted")

    if (camera_handle > 0):
        (KYFG_CameraClose_status,) = KYFG_CameraClose(camera_handle)

    if (grabber_handle != 0):
        (KYFG_Close_status,) = KYFG_Close(grabber_handle)

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

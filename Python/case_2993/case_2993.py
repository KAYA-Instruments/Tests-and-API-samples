# Common KAYA imports DO NOT EDIT!!!
import sys
import os
import argparse
import time
sys.path.insert(0, os.environ['KAYA_VISION_POINT_PYTHON_PATH'])
from KYFGLib import *

# Common Case imports DO NOT EDIT!!!
from enum import IntEnum  # for CaseReturnCode

# additional imports required by particular case, ADD CASE SPECIFIC IMPORTS UNDER THIS LINE:
import threading
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
    parser.add_argument('--number_of_sent_triggers', type=int, default=50, help='Number of sent triggers')

    return parser


def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)


extern_grabbers = []
destroy_external_instances = False
is_cameras_ready = []

def cameras_setter(grabberHandle, index):
    (status,) = KYFG_SetGrabberValueInt(grabberHandle, "CxpConnectionSelector", index)
    # Clear the statistics of the following parameters by writing 0 to them:
    (status,) = KYFG_SetGrabberValueInt(grabberHandle, "TriggerMissedCount", 0)
    (status,) = KYFG_SetGrabberValueInt(grabberHandle, "TriggerSentCount", 0)
    (status,) = KYFG_SetGrabberValueInt(grabberHandle, "TriggerAcknowledgeCount", 0)
    (status,) = KYFG_SetGrabberValueInt(grabberHandle, "TriggerChangeCount", 0)
    # Set GPIO for triggering
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "LineSelector", f'KY_TTL_{index}')
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "LineMode", 'Output')
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "LineSource", f'KY_USER_OUT_0')
    # Set camera trigger
    (status,) = KYFG_SetGrabberValueInt(grabberHandle, "CameraSelector", index)
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "CameraTriggerMode", f'On')
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "CameraTriggerActivation", 'RisingEdge')
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "CameraTriggerSource",
                                                     f'KY_TTL_{index}')
def extern_instance(deviceIndex, instance_index: int):
    global extern_grabbers
    global destroy_external_instances
    global is_cameras_ready
    (extern_grabbers[instance_index],) = KYFG_Open(deviceIndex)
    grabberHandle = extern_grabbers[instance_index]
    (status, camList) = KYFG_UpdateCameraList(grabberHandle)
    (status,) = KYFG_CameraOpen2(camList[instance_index], None)
    cameras_setter(grabberHandle, instance_index)
    is_cameras_ready[instance_index] = True
    print(f'Process {instance_index} is ready')



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
    global extern_grabbers
    global destroy_external_instances
    global is_cameras_ready

    number_of_sent_triggers = args['number_of_sent_triggers']
    (status, device_info) = KY_DeviceInfo(device_index)
    if device_info.m_Protocol != KY_DEVICE_PROTOCOL.KY_DEVICE_PROTOCOL_CoaXPress:
        print('Test could not run on this grabber')
        return CaseReturnCode.COULD_NOT_RUN
    (grabber_handle,) = KYFG_Open(device_index)
    try:
        (status, isSharingSupported) = KYFG_GetGrabberValueInt(grabber_handle, 'SWCapable_InterProcessSharing_Imp')
        if not isSharingSupported:
            print('Grabber sharing is not supported on this device')
            (status,) = KYFG_Close(grabber_handle)
            return CaseReturnCode.COULD_NOT_RUN
    except:
        print('Grabber sharing is not supported on this device')
        (status,) = KYFG_Close(grabber_handle)
        return CaseReturnCode.COULD_NOT_RUN
    (status, camList) = KYFG_UpdateCameraList(grabber_handle)
    assert len(camList) >=2, f'Found {len(camList)} cameras only'
    extern_grabbers = [FGHANDLE() for i in range(len(camList))]
    is_cameras_ready = [False for i in range(len(camList))]
    (status,) = KYFG_CameraOpen2(camList[0], None)
    cameras_setter(grabber_handle, 0)
    is_cameras_ready[0] = True
    extern_grabbers[0] = grabber_handle
    threads = []
    print('Start processes')
    print("Process 0 is ready")
    for i in range(len(camList))[1:]:
        thread = threading.Thread(target=extern_instance, args=(device_index, i))
        threads.append(thread)
        while True:
            if i != 0 and not is_cameras_ready[i-1]:
                time.sleep(0.5)
            else:
                break
        thread.start()
    while True:
        if all(is_cameras_ready):
            break
        else:
            time.sleep(0.5)
    for i in range(number_of_sent_triggers):
        (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabber_handle, "UserOutputSelector", f'UserOutput0')
        (status,) = KYFG_SetGrabberValueBool(grabber_handle, "UserOutputValue", True)
        time.sleep(0.1)
        (status,) = KYFG_SetGrabberValueBool(grabber_handle, "UserOutputValue", False)
    results = []
    for i in range(len(extern_grabbers)):
        KYFG_SetGrabberValueInt(grabber_handle, "CxpConnectionSelector", i)
        results.append(KYFG_GetGrabberValueInt(grabber_handle, "TriggerSentCount")[1])
        print('Trigger sent:', KYFG_GetGrabberValueInt(grabber_handle, "TriggerSentCount"))
    destroy_external_instances = True
    for thread in threads:
        thread.join()
    for result in results:
        assert result == number_of_sent_triggers

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

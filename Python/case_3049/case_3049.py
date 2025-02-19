# Common KAYA imports DO NOT EDIT!!!
import asyncio
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
import queue

result_queue = queue.Queue()
from KYFGLib import *

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
    parser.add_argument('--cameraIndex', type=int, default=0,help='Camera index for this instance')
    parser.add_argument('--number_of_sent_triggers', type=int,default=10, help='Number of sent triggers')
    return parser

def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)
error_count=0
def run_async_function(device_index,camera_index, number_of_sent_triggers):
    result = asyncio.run(new_instance(device_index,camera_index, number_of_sent_triggers))
    result_queue.put(result)
async def new_instance(device_index,camera_index, number_of_sent_triggers):

    instance_process = subprocess.Popen(
        ["python", f"{__file__}",'--unattended', '--deviceIndex',f'{device_index}', "--cameraIndex", f"{camera_index}",
         "--number_of_sent_triggers", f"{number_of_sent_triggers}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        close_fds=True)
    stdout_output, stderr_output = instance_process.communicate()
    print(stdout_output.decode())
    print(stderr_output)
    return_code = instance_process.returncode
    print(return_code)


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
    camera_index=args['cameraIndex']
    number_of_sent_triggers=args['number_of_sent_triggers']
    if camera_index == 0:
        global error_count
    (grabber_handle,) = KYFG_Open(device_index)
    try:
        (status, camera_list,) = KYFG_UpdateCameraList(grabber_handle)
    except:
        time.sleep(7)
        (status, camera_list,) = KYFG_UpdateCameraList(grabber_handle)
    if len(camera_list)==0:
        return CaseReturnCode.NO_HW_FOUND
    if camera_index==0:
        threads = []
        for i in range(1, len(camera_list)):
            thread = threading.Thread(target=run_async_function, args=(device_index, camera_index + i,number_of_sent_triggers))
            threads.append(thread)
            thread.start()

    #Detect camera
    cameraHandle = camera_list[camera_index]
    if camera_index == 0:
        (status,) = KYFG_CameraOpen2(camera_list[0], None)
    else:
        (status,) = KYFG_CameraOpen2(cameraHandle, None)
    # (status,) = KYFG_CameraOpen2(cameraHandle,None)
    (status, camera_info) = KYFG_CameraInfo2(cameraHandle)
    try:
        if KYFG_IsGrabberValueImplemented(grabberHandle, 'TriggerMode'):
            KYFG_SetGrabberValueEnum(grabberHandle, "TriggerMode", 0)
        if not KYFG_IsCameraValueImplemented(cameraHandle, "TriggerMode"):
            return CaseReturnCode.NO_HW_FOUND
    except:
        pass
    camera_master_link = camera_info.master_link
    # Select the "CxpConnectionSelector" where camera is connected (i.e master link of the camera)
    (status,) = KYFG_SetGrabberValueInt(grabber_handle, "CxpConnectionSelector", camera_master_link)
    # Clear the statistics of the following parameters by writing 0 to them:
    (status,) = KYFG_SetGrabberValueInt(grabber_handle, "TriggerMissedCount", 0)
    (status,) = KYFG_SetGrabberValueInt(grabber_handle, "TriggerSentCount", 0)
    (status,) = KYFG_SetGrabberValueInt(grabber_handle, "TriggerAcknowledgeCount", 0)
    (status,) = KYFG_SetGrabberValueInt(grabber_handle, "TriggerChangeCount", 0)
    (status,) = KYFG_SetGrabberValueInt(grabber_handle, "CameraSelector", camera_master_link)
    # Set timer for triggering
    (status,) = KYFG_SetGrabberValueEnum(grabber_handle, "TimerSelector", camera_master_link)
    (status,) = KYFG_SetGrabberValueFloat(grabber_handle, "TimerDelay", 10.0)
    (status,) = KYFG_SetGrabberValueFloat(grabber_handle, "TimerDuration", 10.0)
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabber_handle, "TimerTriggerSource", 'KY_SOFTWARE')
    # Set camera trigger
    try:
        (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabber_handle, "CameraTriggerMode", 'On')
    except:
        print('Trigger Mode is not supported on this camera')
        return CaseReturnCode.NO_HW_FOUND
    print(f'KY_TIMER_ACTIVE_{camera_master_link}')
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabber_handle, "CameraTriggerSource", f'KY_TIMER_ACTIVE_{camera_master_link}')
    for i in range(number_of_sent_triggers):
        print('Stop Loop', datetime.now().time())
        print(f'Sent trigger number {i+1}')
        (status,)=KYFG_GrabberExecuteCommand(grabber_handle, "TimerTriggerSoftware")
        time.sleep(1)
    (status, sent_count)=KYFG_GetGrabberValueInt(grabber_handle, "TriggerSentCount")
    (status, change_count) = KYFG_GetGrabberValueInt(grabber_handle, "TriggerChangeCount")
    print(sent_count, change_count)
    (status,)=KYFG_CameraClose(cameraHandle)
    (status,) = KYFG_Close(grabber_handle)
    if camera_index == 0:
        for thread in threads:
            thread.join()
        results = []
        while not result_queue.empty():
            result = result_queue.get()
            results.append(result)
        print('results = ', results)

    assert sent_count==number_of_sent_triggers, f'TriggerSentCount: {sent_count} is not match to ' \
                                                f'number_of_sent_triggers: {number_of_sent_triggers}'
    assert change_count==number_of_sent_triggers, f'TriggerChangeCount {change_count} is not match to ' \
                                                  f'number_of_sent_triggers {number_of_sent_triggers}'
    if camera_index == 0:
        for res in results:
            assert res == 0, 'Errors while test'
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

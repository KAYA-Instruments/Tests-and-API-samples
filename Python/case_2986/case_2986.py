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

sys.path.insert(0, os.environ['KAYA_VISION_POINT_PYTHON_PATH'])
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
    parser.add_argument('--cameraIndex', type=int, default=0, help='Camera index for this instance')
    parser.add_argument('--number_of_sent_tests', type=int, default=3, help='Number of sent triggers')
    return parser

def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)

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
    #try:
    #    (status, isSharingSupported) = KYFG_GetGrabberValueInt(grabber_handle, 'SWCapable_InterProcessSharing_Imp')
    #    if not isSharingSupported:
    #        print('Grabber sharing is not supported on this device')
    #        (status,) = KYFG_Close(grabber_handle)
    #        return CaseReturnCode.COULD_NOT_RUN
    #except:
    #    print('Grabber sharing is not supported on this device')
    #    (status,) = KYFG_Close(grabberHandle)
    #    return CaseReturnCode.COULD_NOT_RUN
    (status, camera_list,) = KYFG_UpdateCameraList(grabber_handle)
    for cam in camera_list:
        (status,camInfo)=KYFG_CameraInfo2(cam)
        if 'Chameleon' in camInfo.deviceModelName:
            camera_list.remove(cam)
            print(f'Camera {camInfo.deviceModelName} removed from camera list for test')
    if camera_index == 0:
        if len(camera_list) == 0:
            return CaseReturnCode.NO_HW_FOUND
        threads = []
        for i in range(1, len(camera_list)):
            thread = threading.Thread(target=new_instance, args=(device_index,camera_index+i, number_of_sent_tests,))
            threads.append(thread)
            thread.start()
            time.sleep(10)
    # Detect camera
    cameraHandle = camera_list[camera_index]
    if camera_index==0:
        (status,) = KYFG_CameraOpen2(camera_list[0], None)
    else:
        (status,) = KYFG_CameraOpen2(cameraHandle, None)

    (status, camera_info) = KYFG_CameraInfo2(cameraHandle)
    camera_master_link = camera_info.master_link
    # Select the "CxpConnectionSelector" where camera is connected (i.e master link of the camera)
    (status, CxpConnectionSelectorMax, CxpConnectionSelectorMin) = KYFG_GetGrabberValueIntMaxMin(grabber_handle, "CxpConnectionSelector")
    if CxpConnectionSelectorMax < 0:
        camera_master_link = 0
    else:
        (status,) = KYFG_SetGrabberValueInt(grabber_handle, "CxpConnectionSelector", camera_master_link)
    for i in range(number_of_sent_tests):
        print('Start Loop', datetime.now().time())
        (status,) = KYFG_SetCameraValueInt(cameraHandle, "CxpConnectionTestRxPacketCount", 0)
        (status,) = KYFG_SetCameraValueInt(cameraHandle, "CxpConnectionTestTxPacketCount", 0)
        (status,) = KYFG_SetCameraValueEnum(cameraHandle, "CxpConnectionTestMode", 1)
        (status,) = KYFG_SetGrabberValueInt(grabber_handle, "CxpConnectionTestTxPacketCount", 0)
        (status,) = KYFG_SetGrabberValueInt(grabber_handle, "CxpConnectionTestRxPacketCount", 0)
        (status,) = KYFG_SetGrabberValueEnum(grabber_handle, "CxpConnectionTestMode", 1)
        waitFortime(10)
        (status,) = KYFG_SetCameraValueEnum(cameraHandle, "CxpConnectionTestMode", 0)
        (status,) = KYFG_SetGrabberValueEnum(grabber_handle, "CxpConnectionTestMode", 0)
        (status, camera_rx_count) = KYFG_GetCameraValueInt(cameraHandle, "CxpConnectionTestRxPacketCount")
        (status, camera_tx_count) = KYFG_GetCameraValueInt(cameraHandle, "CxpConnectionTestTxPacketCount")
        (status, grabber_rx_count) = KYFG_GetGrabberValueInt(grabber_handle, "CxpConnectionTestRxPacketCount")
        (status, grabber_tx_count) = KYFG_GetGrabberValueInt(grabber_handle, "CxpConnectionTestTxPacketCount")
        print('Stop Loop', datetime.now().time())
        print(f'camera_rx_count {camera_rx_count}')
        print(f'grabber_tx_count {grabber_tx_count}')
        print(f'camera_tx_count {camera_tx_count}')
        print(f'grabber_rx_count {grabber_rx_count}')
        assert camera_rx_count>0, f'camera_rx_count is {camera_rx_count}'
        assert grabber_tx_count > 0, f'camera_rx_count is {grabber_tx_count}'
        assert camera_tx_count > 0, f'camera_rx_count is {camera_tx_count}'
        assert grabber_rx_count > 0, f'camera_rx_count is {grabber_rx_count}'
    if camera_index == 0:
        for thread in threads:
            thread.join()
    if camera_index==0:
        assert errorCount==0, 'Not all cameras are successfully working'

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


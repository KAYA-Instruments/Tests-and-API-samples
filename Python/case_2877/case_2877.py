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
    parser.add_argument('--BandwidthTestPayloadBufferSize', default=4097.0, type=float,
                        help='Bandwidth Test Pay load Buffer Height')
    parser.add_argument('--BandwidthTestPayloadBuffersCount', default=1,type=int,
                        help='Bandwidth Test Payload BuffersCount')
    parser.add_argument('--PCIMiddleBandwidth',default=6500, type=int, help='The actual bandwidth')
    return parser

def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)

def waitForSpeedTest(seconds: int):
    threadSleepSeconds = seconds
    print(f"Thread sleep for {threadSleepSeconds} seconds: ")
    for remaining in range(threadSleepSeconds, 0, -1):

        sys.stdout.write("\r")
        sys.stdout.write("{:2d} seconds remaining".format(remaining))
        sys.stdout.flush()
        time.sleep(1)
    sys.stdout.write("\rComplete!            \n")
    return threadSleepSeconds


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
    # Check grabber
    (status, device_info) = KY_DeviceInfo(device_index)
    if device_info.m_Protocol != KY_DEVICE_PROTOCOL.KY_DEVICE_PROTOCOL_CoaXPress:
        print('Test could not run on this grabber')
        return CaseReturnCode.COULD_NOT_RUN
    (grabberHandle,) = KYFG_Open(device_index)
    bufferSizeTest=args['BandwidthTestPayloadBufferSize']
    bufferCountTest=args['BandwidthTestPayloadBuffersCount']
    PCIMiddleBandwidth=args['PCIMiddleBandwidth']
    averfgeSpeedList=[]
    (status,) = KYFG_SetGrabberValueFloat(grabberHandle, "BandwidthTestPayloadBufferSize", bufferSizeTest)
    (status,) = KYFG_SetGrabberValueInt(grabberHandle, "BandwidthTestPayloadBuffersCount", bufferCountTest)
    (status,) = KYFG_GrabberExecuteCommand(grabberHandle, "BandwidthTestPerform")
    (status, id, status_value) = KYFG_GetGrabberValue(grabberHandle, "BandwidthTestStatus")
    while True:
        if status_value=='Finished':
            break
        else:
            time.sleep(0.1)
            (status, id, status_value) = KYFG_GetGrabberValue(grabberHandle, "BandwidthTestStatus")
        assert status_value!='Error' and status_value!='Stopped', f'BandwidthTestStatus: {status_value}'


    (status, speedValue) = KYFG_GetGrabberValueFloat(grabberHandle, "BandwidthTestAverageSpeed")
    print(f'Average transfer speed is {speedValue} MB/sec')
    averfgeSpeedList.append(speedValue)

    for i in averfgeSpeedList:
        assert i>=PCIMiddleBandwidth-500 and i<=PCIMiddleBandwidth+500, 'The average speed not in boundaries'
    KYFG_Close(grabberHandle)
    print(f'\nExiting from CaseRun({args}) with code 0...')
    return CaseReturnCode.SUCCESS


def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)

if __name__ == "__main__":
    try:
        args_ = ParseArgs()
        return_code = CaseRun(args_)
        print(f'Case return code: {return_code}')
    except Exception as ex:
        print(f"Exception of type {type(ex)} occurred: {str(ex)}")
        exit(-200)

    exit(return_code)

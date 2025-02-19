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
    parser.add_argument('--outputLine', default='KY_OPTO_OUT_0', type=str, help='Output line')
    parser.add_argument('--inputLine', default='KY_OPTO_IN_0', type=str, help='input line')
    parser.add_argument('--expectedPulseRate', default=10, type=int, help='Triggers per second')
    parser.add_argument('--duration', default=3, type=int, help='Duration of trigger generation')

    return parser

def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)
class AUXCallbackStruct:
    def __init__(self):
        self.callbackCounter = 0
        return
def AUXCallbackFunction(buffHandle, userContext):
    callback_struct = cast(userContext, py_object).value
    callback_struct.callbackCounter += 1

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
    outputLine = args['outputLine']
    inputLine = args['inputLine']
    expectedPulseRate = args['expectedPulseRate']
    duration = args['duration']
    (grabberHandle,) = KYFG_Open(device_index)
    (status, camList) = KYFG_UpdateCameraList(grabberHandle)
    assert len(camList) > 0, 'There are no cameras on this list'
    (status,) = KYFG_CameraOpen2(camList[0],None)
    aux_callback_struct = AUXCallbackStruct()
    # Output line setting
    (status,) = KYFG_AuxDataCallbackRegister(grabberHandle, AUXCallbackFunction, py_object(aux_callback_struct))
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "LineSelector", f"{outputLine}")
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "LineMode", "Output")
    (status,) = KYFG_SetGrabberValueBool(grabberHandle, "LineInverter", False)
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "LineSource", "KY_TIMER_ACTIVE_0")
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "LineEventMode", "Disabled")
    # Input line setting
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "LineSelector", f"{inputLine}")
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "LineMode", "Input")
    (status,) = KYFG_SetGrabberValueBool(grabberHandle, "LineInverter", False)
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "LineSource", "KY_DISABLED")
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "LineEventMode", "Disabled")
    # Timer setting
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "TimerSelector", "Timer0")
    timer_delay = timer_duration = 1e6/expectedPulseRate/2
    (status,) = KYFG_SetGrabberValueFloat(grabberHandle, "TimerDelay", timer_delay)
    (status,) = KYFG_SetGrabberValueFloat(grabberHandle, "TimerDuration", timer_duration)
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "TimerActivation", "RisingEdge")
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "TimerTriggerSource", "KY_DISABLED")
    # Grabber trigger setting
    (status,) = KYFG_SetGrabberValueEnum(grabberHandle, "TriggerMode", 1)
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "TriggerSource", inputLine)
    (status,) = KYFG_SetGrabberValueFloat(grabberHandle, "TriggerFilter", 1.)
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "TriggerEventMode", "RisingEdge")
    # Start trigger generation
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "TimerTriggerSource", "KY_CONTINUOUS")
    time.sleep(duration)
    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "TimerTriggerSource", "KY_DISABLED")
    print("CallbackCounter:", aux_callback_struct.callbackCounter)
    (status,) = KYFG_SetGrabberValueEnum(grabberHandle, "TriggerMode", 0)
    (status,) = KYFG_CameraClose(camList[0])
    (status,) = KYFG_Close(grabberHandle)
    assert abs(aux_callback_struct.callbackCounter-(expectedPulseRate*duration)) < (expectedPulseRate*duration)/100

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

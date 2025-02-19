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
import xml.etree.ElementTree as ET
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
    return parser

def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)


grabberParameters = {}
errorCount = 0

class Grabber:
    def __init__(self, grabberName: str, grabberHandle: FGHANDLE):
        self.grabberName = grabberName
        self.grabberHandle = grabberHandle
        self.isCallbackEnd = False

def grabberCallback(userContext, pParameterDescriptorPtr, grouppingLevel):
    global grabberParameters
    grabber_obj = cast(userContext, py_object).value
    if grabber_obj.isCallbackEnd:
        return
    if pParameterDescriptorPtr.interfaceType != ParameterInterfaceType.ICommand and pParameterDescriptorPtr.isWritable \
            and pParameterDescriptorPtr.interfaceType != ParameterInterfaceType.ICategory:
        grabberParameters[pParameterDescriptorPtr.paramName] = {"descriptor": pParameterDescriptorPtr}


def get_enums_from_xml(grabberHendle, paramName):
    # (KYFG_CameraGetXML_status, isZipped, buffer) = KYFG_CameraGetXML(camHandle)
    grabber_xml_file = pathlib.Path(os.environ.get("KAYA_VISION_POINT_BIN_PATH")).joinpath("KYFGLib.xml")

    xmlContent = None

    with grabber_xml_file.open('r') as camera_xml:
        xmlContent = camera_xml.read()
    root = ET.fromstring(xmlContent)
    ns = '{http://www.genicam.org/GenApi/Version_1_1}'
    test_patterns = []
    for group in root.findall(f".//*[@Name='{paramName}']/{ns}EnumEntry"):
        pattern_value = group.find(f"{ns}Value").text
        pattern_name = group.attrib.get("Name")
        test_patterns.append({"name": pattern_name, "value": pattern_value})
    if os.path.exists(f"{os.path.dirname(__file__)}/camera_xml.zip"):
        os.remove(f"{os.path.dirname(__file__)}/camera_xml.zip")
    return test_patterns


def set_grabber_values(grabberHandle, param_name, interfaceType, list_index: int = 0):
    global grabberParameters
    global errorCount
    current_value = None
    value_for_set = None
    descriptor = grabberParameters[param_name]['descriptor']
    try:
        (status, enum, current_value) = KYFG_GetGrabberValue(grabberHandle, param_name)
    except:
        (status, current_value) = KYFG_GetGrabberValue(grabberHandle, param_name)
    # Set enum values
    if interfaceType == ParameterInterfaceType.IEnumeration or interfaceType == ParameterInterfaceType.IEnumEntry:
        value_list = get_enums_from_xml(grabberHandle, "SilentDiscovery")
        for value_dict in value_list:
            if value_dict['name'] != current_value:
                try:
                    (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, param_name, value_dict['name'])
                    (status, enum, grabberParameters[param_name]['new_value']) = KYFG_GetGrabberValue(grabberHandle,
                                                                                                      param_name)
                    return
                except:
                    pass
    # Set int values
    elif interfaceType == ParameterInterfaceType.IInteger:
        if not descriptor.minIntValue <= current_value <= descriptor.maxIntValue:
            print(f"ERROR {param_name} not in range {descriptor.minIntValue}, {descriptor.maxIntValue}")
            errorCount += 1
            return
        try:
            value_for_set = random.choice(range(descriptor.minIntValue, descriptor.maxIntValue, descriptor.incIntValue))
        except:
            value_for_set = descriptor.minIntValue
    # Set float values
    elif interfaceType == ParameterInterfaceType.IFloat:
        if not descriptor.minFloatValue <= current_value <= descriptor.maxFloatValue:
            print(f"ERROR {param_name} not in range {descriptor.minFloatValue}, {descriptor.maxFloatValue}")
            errorCount += 1
            return
        try:
            value_for_set = random.choice(range(descriptor.minFloatValue, descriptor.maxFloatValue, descriptor.incFloatValue))
        except:
            value_for_set = descriptor.minIntValue
    # Set bool values
    elif interfaceType == ParameterInterfaceType.IBoolean:
        value_for_set = True if current_value == False else False
    try:
        (status,) = KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, param_name, value_for_set)
    except:
        pass
    try:
        (status, grabberParameters[param_name]['new_value']) = KYFG_GetGrabberValue(grabberHandle, param_name)
    except:
        (status, enum, grabberParameters[param_name]['new_value']) = KYFG_GetGrabberValue(grabberHandle, param_name)
def get_grabber_values(grabberHandle, paramName, expected_value):
    global errorCount
    try:
        (status, enum, current_value) = KYFG_GetGrabberValue(grabberHandle, paramName)
    except:
        (status, current_value) = KYFG_GetGrabberValue(grabberHandle, paramName)
    if expected_value != current_value:
        print(f'ERROR! {paramName} is not setted correctly')
        print(f'expected_value: {expected_value}; current_value: {current_value}')
        errorCount += 1
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
    global grabberParameters
    (grabberHandle,) = KYFG_Open(device_index)
    (status, grabberInfo) = KY_DeviceInfo(device_index)
    (status, cameraList) = KYFG_UpdateCameraList(grabberHandle)
    for cameraHandle in cameraList:
        (status,) = KYFG_CameraOpen2(cameraHandle, None)
    grabber_obj = Grabber(grabberInfo.szDeviceDisplayName, grabberHandle)
    (status,) = KY_RegisterGrabberConfigurationParameterCallback(grabberHandle, grabberCallback, py_object(grabber_obj))
    KY_GetGrabberConfigurationParameterDefinitions(grabberHandle)
    grabber_obj.isCallbackEnd = True
    for key, val in grabberParameters.items():
        set_grabber_values(grabberHandle, key, val['descriptor'].interfaceType)
        print(key, val['descriptor'], val['new_value'])
    for key, val in grabberParameters.items():
        get_grabber_values(grabberHandle, key, val['new_value'])
    for cameraHandle in cameraList:
        (status,) = KYFG_CameraClose(cameraHandle)
    (status,) = KYFG_Close(grabberHandle)
    print(f'Error count: {errorCount}')
    assert errorCount == 0, "Test not passed"
    print(f'\nExiting from CaseRun({args}) with code SUCCESS...')
    return CaseReturnCode.SUCCESS

# The flow starts here
if __name__ == "__main__":
    # try:
    args_ = ParseArgs()
    return_code = CaseRun(args_)
    print(f'Case return code: {return_code}')
# except Exception as ex:
#     print(f"Exception of type {ty

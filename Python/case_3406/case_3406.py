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
import random
import string


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

class Camera:
    def __init__(self, deviceModelName, cameraHandle):
        self.modelName = deviceModelName
        self.cameraHandle = cameraHandle
        self.nodes = {}
        self.enumValues = {}
        self.xmlErrorsList = []
        self.getEnumEntryVal = False
    def clearNodes(self):
        self.nodes = {}
        self.enumValues = {}
        self.getEnumEntryVal = False
    def print_xml_errors(self):
        if len(self.xmlErrorsList) > 0:
            print('*'*32, 'XML ERRORS', "*"*32)
            for name in self.xmlErrorsList:
                print(f'{name} have a pInvalidator value')

    def print_nodes(self):
        for k, v in self.nodes.items():
            print(k, v)

    def print_enum_values(self):
        for k,v in self.enumValues.items():
            print(k, v)

    def print_enumeration_nodes_values(self):
        for k,v in self.nodes.items():
            if self.enumValues.get(k):
                print(k, self.enumValues.get(k))

    def __eq__(self, other):
        if isinstance(other, Camera):
            result = True
            if self.modelName != other.modelName or self.cameraHandle != other.cameraHandle:
                print(f"It's other camera: {self.modelName} != {other.modelName}")
                return False
            for next_param in other.nodes.keys():
                node = other.nodes.get(next_param)
                match node.interfaceType:
                    case ParameterInterfaceType.IEnumeration:
                        (status, new_value) = KYFG_GetCameraValueStringCopy(self.cameraHandle, next_param)
                        if node.curStringValue != new_value:
                            print(f'{next_param} is not setted correctly: {node.curSelectorValue} - {new_value}')
                            result = False
                    case ParameterInterfaceType.IFloat:
                        (status, new_value) = KYFG_GetCameraValueFloat(self.cameraHandle, next_param)
                        if node.curFloatValue != new_value:
                            print(f'{next_param} is not setted correctly: {node.curFloatValue} - {new_value}')
                            result = False
                    case ParameterInterfaceType.IString:
                        (status, new_value) = KYFG_GetCameraValueStringCopy(self.cameraHandle, next_param)
                        if node.curStringValue != new_value:
                            print(f'{next_param} is not setted correctly: {node.curStringValue} - {new_value}')
                            result = False
                    case ParameterInterfaceType.IInteger:
                        (status, new_value) = KYFG_GetCameraValueInt(self.cameraHandle, next_param)
                        if node.curIntValue != new_value:
                            print(f'{next_param} is not setted correctly: {node.curIntValue} - {new_value}')
                            result = False
                    case ParameterInterfaceType.IBoolean:
                        (status, new_value) = KYFG_GetCameraValueBool(self.cameraHandle, next_param)
                        if node.curBoolValue != new_value:
                            print(f'{next_param} is not setted correctly: {node.curBoolValue} - {new_value}')
                            result = False
            return result



class NewValuesCreator:
    @staticmethod
    def create_int_value(node):
        return int(random.randint(node.minIntValue, node.maxIntValue)/node.incIntValue)*node.incIntValue
    @staticmethod
    def create_float_value(node):
        return (round(random.uniform(node.minFloatValue, node.maxFloatValue), 2))/node.incFloatValue*node.incFloatValue
    @staticmethod
    def create_bool_value(node):
        return True if not node.curBoolValue else False
    @staticmethod
    def create_str_value():
        return ''.join(random.choices([chr(i) for i in range(97,122)], k=8))  # k = length of the string
    @staticmethod
    def create_enum_value(node,camera_object: Camera):
        return camera_object.enumValues[node.paramName][random.randint(0, len(camera_object.enumValues[node.paramName])-1)]
def is_userSetLoadReg_invalidator(camHandle, paramName):
    try:
        (status, pInvalidatorValue) = KY_GetCameraPropertyParameterValue(camHandle, paramName, 'pInvalidator')
        if 'UserSetLoadReg' not in pInvalidatorValue:
            (status, pValue) = KY_GetCameraPropertyParameterValue(camHandle, paramName, 'pValue')
            (status, pInvalidator) = KY_GetCameraPropertyParameterValue(camHandle, pValue, 'pInvalidator')
            if 'UserSetLoadReg' not in pInvalidator:
                return False
        return True
    except:
        try:
            (status, pValue) = KY_GetCameraPropertyParameterValue(camHandle, paramName, 'pValue')
            (status, pInvalidator) = KY_GetCameraPropertyParameterValue(camHandle, pValue, 'pInvalidator')
            if 'UserSetLoadReg' not in pInvalidator:
                return False
            return True
        except:
            return False
def CameraConfigurationParameterCallback(userContext, descriptor, groupLevel):
    camera_obj = cast(userContext, py_object).value
    if is_userSetLoadReg_invalidator(camera_obj.cameraHandle, descriptor.paramName):
        camera_obj.nodes[descriptor.paramName] = descriptor
        if descriptor.interfaceType == ParameterInterfaceType.ICommand:
            camera_obj.xmlErrorsList.append(descriptor.paramName)
    if descriptor.interfaceType == ParameterInterfaceType.IEnumeration and descriptor.paramName not in camera_obj.enumValues.keys():
        camera_obj.enumValues[descriptor.paramName] = []
    elif descriptor.interfaceType == ParameterInterfaceType.IEnumEntry:
        param_name = list(camera_obj.enumValues.keys())[-1]
        if param_name not in camera_obj.enumValues.keys():
            camera_obj.enumValues[param_name] = []
        camera_obj.enumValues[param_name].append(descriptor.paramName)
def updateCameraParameters(cameraHandle, object: Camera):
    object.clearNodes()
    (status,) = KY_RegisterCameraConfigurationParameterCallback(cameraHandle, CameraConfigurationParameterCallback, py_object(object))
    (status,) = KY_GetCameraConfigurationParameterDefinitions(cameraHandle)
    (status,) = KY_UnregisterCameraConfigurationParameterCallback(cameraHandle, CameraConfigurationParameterCallback)
    list_for_removing = []
    for name, node in object.nodes.items():
        if not node.isWritable or not node.isAvailable:
            list_for_removing.append(name)
    for nextName in list_for_removing:
        del object.nodes[nextName]
def get_new_node_value(node, camera_obj):
    match node.interfaceType:
        case ParameterInterfaceType.IEnumeration:
            return NewValuesCreator.create_enum_value(node, camera_obj)
        case ParameterInterfaceType.IBoolean:
            return NewValuesCreator.create_bool_value(node)
        case ParameterInterfaceType.IFloat:
            return NewValuesCreator.create_float_value(node)
        case ParameterInterfaceType.IInteger:
            return NewValuesCreator.create_int_value(node)
        case ParameterInterfaceType.IString:
            return NewValuesCreator.create_str_value()
def deviceEventCallbackFunc(userContext, GencpEventObj):
    if GencpEventObj.deviceEvent.eventId == KYDEVICE_EVENT_ID.KYDEVICE_EVENT_CAMERA_CONNECTION_LOST_ID:
        print('Camera Reset')
        (status,) = KYFG_CameraClose(GencpEventObj.camHandle)
def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)
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
    (grabberHandle,) = KYFG_Open(device_index)
    (status, cameraList) = KYFG_UpdateCameraList(grabberHandle)
    (status,) = KYDeviceEventCallBackRegister(grabberHandle, deviceEventCallbackFunc, None)
    error_count = 0
    assert len(cameraList) > 0, "0 cameras detected"
    print(len(cameraList), "Cameras detected")
    isIronFound = False
    for i in range(len(cameraList)):
        cameraHandle = cameraList[i]
        (status, camInfo) = KYFG_CameraInfo2(cameraHandle)
        if 'Iron' not in camInfo.deviceModelName:
            continue
        isIronFound = True
        print(f'Camera {camInfo.deviceModelName} opened for test')
        camera_obj = Camera(camInfo.deviceModelName, cameraHandle)
        (status,) = KYFG_CameraOpen2(cameraHandle, None)
        updateCameraParameters(cameraHandle, camera_obj)
        camera_obj.print_xml_errors()
        print('*' * 32, 'SETTING ERRORS', "*" * 32)
        for node in camera_obj.nodes.values():
            if (node.interfaceType not in [ParameterInterfaceType.ICommand, ParameterInterfaceType.IRegister]
                    and node.isWritable and node.isAvailable):
                try:
                    new_value = get_new_node_value(node, camera_obj)
                    (status,) = KYFG_SetCameraValue(cameraHandle, node.paramName, new_value)
                except:
                    print(node.paramName, new_value, 'not set')
                    continue

        KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "UserSetSelector", "UserSet1")
        KYFG_CameraExecuteCommand(cameraHandle, "UserSetSave")

        updated_camera_obj = Camera(camInfo.deviceModelName, cameraHandle)
        updateCameraParameters(cameraHandle, updated_camera_obj)

        KYFG_CameraExecuteCommand(cameraHandle, "DeviceReset")
        time.sleep(10)  # wait for camera power-up
        (status, camList) = KYFG_UpdateCameraList(grabberHandle)
        (status,) = KYFG_CameraOpen2(cameraHandle, None)
        KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "UserSetSelector", "UserSet1")
        KYFG_CameraExecuteCommand(cameraHandle, "UserSetLoad")
        loaded_camera_obj = Camera(camInfo.deviceModelName, cameraHandle)
        updateCameraParameters(cameraHandle, loaded_camera_obj)
        if not updated_camera_obj == loaded_camera_obj:
            error_count += 1
            print("Camera Load UNSUCCESSFUL ")
        else:
            print("Camera Load successful ")
        (status,) = KYFG_CameraClose(cameraHandle)
    if not isIronFound:
        return CaseReturnCode.NO_HW_FOUND
    (status,) = KYFG_Close(grabberHandle)
    assert not error_count, 'Test not Passed'
    print(f'\nExiting from CaseRun({args}) with code SUCCESS...')
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

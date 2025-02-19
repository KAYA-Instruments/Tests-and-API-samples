# Common KAYA imports DO NOT EDIT!!!
import sys
import os
import argparse
sys.path.insert(0, os.environ['KAYA_VISION_POINT_PYTHON_PATH'])
import KYFGLib
from KYFGLib import *

# Common Case imports DO NOT EDIT!!!
from enum import IntEnum  # for CaseReturnCode

# additional imports required by particular case, ADD CASE SPECIFIC IMPORTS UNDER THIS LINE:
import zipfile
import io
import xml.etree.ElementTree as ET
import pathlib
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
    parser.add_argument('--camera', type=str, default='Chameleon', help='Camera model name for test')

    return parser

def extract_from_zip(buffer:list):
    # bytes_buffer = [bytes([i]) for i in buffer]
    bytes_buffer = bytes(buffer)
    buffer_io = io.BytesIO(bytes_buffer)
    extracted_files = {}
    with zipfile.ZipFile(buffer_io, 'r') as zip_ref:
        file_names = zip_ref.namelist()
        for file_name in file_names:
            with zip_ref.open(file_name) as file:
                extracted_files[file_name] = file.read().decode()
    return extracted_files

def remove_elements(element, tags_to_delete, text_values_to_delete):
    for child in list(element):
        remove_elements(child, tags_to_delete, text_values_to_delete)
        if child.text and child.text.strip() in text_values_to_delete:
            element.remove(child)
        elif "Name" in child.attrib.keys():
            if child.attrib["Name"] in text_values_to_delete:
                element.remove(child)
def change_xml_file(xml_data):
    root = ET.fromstring(xml_data)

    commands_to_delete = ["AcquisitionStart"]
    tags_to_delete = ["Command", "pFeature", "pValue", "IntReg"]
    remove_elements(root, tags_to_delete, commands_to_delete)

    new_xml_data = ET.tostring(root).decode()
    return new_xml_data
def save_xml_file(xml_path:str, data):
    with open(xml_path, 'w') as xml:
        xml.write(data)
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
    assert len(cameraList) > 0, "There are no cameras on this grabber"
    camera_model = args['camera']
    cameraHandle = None
    for cam in cameraList:
        (status, camInfo) = KYFG_CameraInfo2(cam)
        if str(camera_model).lower() in str(camInfo.deviceModelName).lower():
            cameraHandle = cam
            break
    if cameraHandle is None:
        print(f"Camera {camera_model} not found")
        return CaseReturnCode.NO_HW_FOUND
    (status, camInfo) = KYFG_CameraInfo2(cameraHandle)
    (status,) = KYFG_CameraOpen2(cameraHandle, None)
    print(camInfo.deviceModelName, 'is opened for test')
    (status, is_zipped_file, buffer) = KYFG_CameraGetXML(cameraHandle)
    (status,) = KYFG_CameraClose(cameraHandle)
    if is_zipped_file:
        files_dict = extract_from_zip(buffer)
    else:
        files_dict = {f"{camInfo.deviceModelName}.xml": "".join(buffer)}
    file_path = None
    for file_name, file_data in files_dict.items():
        new_file_data = change_xml_file(file_data)
        file_path = pathlib.Path(__file__).parent.joinpath(file_name).absolute().as_posix()
        save_xml_file(file_path, new_file_data)

    (status,) = KYFG_CameraOpen2(cameraHandle, file_path)
    KYFG_SetGrabberValueEnum_ByValueName(grabberHandle, "TransferControlMode", "UserControlled")
    (status, streamHandle) = KYFG_StreamCreate(cameraHandle, 0)
    buffers = [0 for i in range(16)]
    (status, payloadSize, _ , _) = KYFG_StreamGetInfo(streamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_PAYLOAD_SIZE)
    for IFrame in buffers:
        (status, buffers[IFrame]) = KYFG_BufferAllocAndAnnounce(streamHandle, payloadSize, 0)
    is_test_passed = False
    try:
        (status,) = KYFG_CameraStart(cameraHandle, streamHandle, 0)
        KYFG_CameraExecuteCommand(cameraHandle, "AcquisitionStart")
    except KYFGLib.KYException as e:
        print(type(e), str(e), "Successfully got! Test Passed")
        is_test_passed = True
    (status,) = KYFG_CameraStop(cameraHandle)
    (status,) = KYFG_StreamDelete(streamHandle)
    (status,) = KYFG_CameraClose(cameraHandle)
    (status,) = KYFG_Close(grabberHandle)
    assert is_test_passed, "Test failed"
    pathlib.Path(file_path).unlink()
    print(f'\nExiting from CaseRun({args}) with code SUCCESS...')
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


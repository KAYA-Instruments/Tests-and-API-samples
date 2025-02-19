# Common KAYA imports DO NOT EDIT!!!
import sys
import os
import argparse
sys.path.insert(0, os.environ['KAYA_VISION_POINT_PYTHON_PATH'])
from KYFGLib import *

# Common Case imports DO NOT EDIT!!!
from enum import IntEnum  # for CaseReturnCode

# additional imports required by particular case, ADD CASE SPECIFIC IMPORTS UNDER THIS LINE:
from zipfile import ZipFile
import time
import xml.etree.ElementTree as ET
import numpy as np


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


def get_enums_from_xml(camHandle, paramName):
    (KYFG_CameraGetXML_status, isZipped, buffer) = KYFG_CameraGetXML(camHandle)
    if isZipped == False:
        xmlContent = ''.join(buffer)
    else:
        newFile = open(f"{os.path.dirname(__file__)}/camera_xml.zip", "wb")
        newFile.write(bytes(buffer))
        newFile.close()
        with ZipFile(f"{os.path.dirname(__file__)}/camera_xml.zip", "r") as zipxml:
            for name in zipxml.namelist():
                _, ext = os.path.splitext(name)
                if ext == '.xml':
                    with zipxml.open(name) as camera_xml:
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

camHandleArray = {}
def get_bitness(camHandle):
    (status, camera_pixel_format_int, camera_pixel_format) = KYFG_GetCameraValue(camHandle, "PixelFormat")

    if camera_pixel_format.endswith("8"):
        return 8
    elif camera_pixel_format.endswith("10"):
        return 10
    elif camera_pixel_format.endswith("12"):
        return 12
    
    return CaseReturnCode.SUCCESS

def unpack(content, bitness):
    BYTE = 8
    unpacked_bytes = []

    f_mask = 2**8-1
    s_mask = (2**bitness - 1) ^ f_mask
    
    bytes_length = int(bitness / 2)
    bits_count = int(bytes_length * BYTE)
    
    for i in range(0, len(content), bytes_length):
        pixels = [format(b, 'b').zfill(BYTE) for b in content[i:i+bytes_length]]
        pixels.reverse()
        p_str = ''.join(pixels)
        for j in range(bits_count, 0, -bitness):
            pixel = int(p_str[j-bitness:j], 2)
            unpacked_bytes.append(pixel & f_mask)
            unpacked_bytes.append((pixel & s_mask) >> BYTE)
    
    return unpacked_bytes


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

    (grabber_handle,) = KYFG_Open(device_index)
    (_, camHandleArray[device_index]) = KYFG_UpdateCameraList(grabber_handle)
    cams_num = len(camHandleArray[device_index])

    if cams_num == 0:
        print('No cameras found on this device!')
        return CaseReturnCode.NO_HW_FOUND
    error_count=0
    for i in range(cams_num):
        camera_handle = camHandleArray[device_index][i]
        KYFG_CameraOpen2(camera_handle, None)
        (status, cameraInfo) = KYFG_CameraInfo(camera_handle)
        print(f'Camera {cameraInfo.deviceModelName} is open')
        KYFG_SetGrabberValueEnum_ByValueName(grabber_handle, 'PackedDataMode', 'Unpacked')
        available_test_patterns = get_enums_from_xml(camera_handle, 'TestPattern')
        if len(available_test_patterns)==0:
            available_test_patterns = get_enums_from_xml(camera_handle, 'PatternType')

        test_pattern = None
        for pattern in available_test_patterns:
            if pattern.get('value', '0') != '0':
                test_pattern = pattern.get('name')
                break

        # if not test_pattern:
        #     print('Required hardware not found')
        #     return CaseReturnCode.NO_HW_FOUND
        if 'Chameleon' in cameraInfo.deviceModelName:
            KYFG_SetCameraValueEnum(camera_handle, "VideoSourcePatternType", 6)
            KYFG_SetCameraValueEnum_ByValueName(camera_handle, "PixelFormat", 'RGB12')
        else:
            try:
                KYFG_SetCameraValueEnum_ByValueName(camera_handle, 'TestPattern', test_pattern)
                KYFG_SetCameraValueEnum_ByValueName(camera_handle, "PixelFormat", 'Mono10')
            except:
                KYFG_SetCameraValueEnum_ByValueName(camera_handle, "PixelFormat", 'BayerBG10')

        bitness = get_bitness(camera_handle)
        if not bitness:
            print('Unable to detect camera bit depth')
            continue
        if bitness == 8:
            print("Pixel format is 8 and the raw data will not be unpacked")
            continue

        (_, stream_handle) = KYFG_StreamCreateAndAlloc(camera_handle, 16, 0)
        (buffSize,) = KYFG_StreamGetSize(stream_handle)

        KYFG_CameraStart(camera_handle, stream_handle, 1)
        time.sleep(0.5)
        KYFG_CameraStop(camera_handle)
        (buffData,) = KYFG_StreamGetPtr(stream_handle, 0)
        buffContent = ctypes.string_at(buffData, size=buffSize)
        unpacked_buffer_data = np.array(bytearray(buffContent))
        KYFG_StreamDelete(stream_handle)

        KYFG_SetGrabberValueEnum_ByValueName(grabber_handle, 'PackedDataMode', 'Packed_RowAligned32')
        (_, stream_handle) = KYFG_StreamCreateAndAlloc(camera_handle, 1, 0)
        (buffSize,) = KYFG_StreamGetSize(stream_handle)

        KYFG_CameraStart(camera_handle, stream_handle, 1)
        time.sleep(0.5)
        KYFG_CameraStop(camera_handle)
        (buffData,) = KYFG_StreamGetPtr(stream_handle, 0)

        buffContent_pack = ctypes.string_at(buffData, size=buffSize)
        unpacked_result_data = np.array(unpack(buffContent_pack, bitness))

        if np.array_equal(unpacked_buffer_data, unpacked_result_data):
            print(f'Raw data are equal on camera {cameraInfo.deviceModelName}')
        else:
            print('raw data are not equal')
            error_count+=1
        (status,) = KYFG_CameraClose(camera_handle)


    KYFG_Close(grabber_handle)
    assert error_count==0, 'There are errors while test'
    print(f'\nExiting from CaseRun({args}) with code 0...')
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
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
import numpy as np
from zipfile import ZipFile
import xml.etree.ElementTree as ET


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
    parser.add_argument('--camera', type=str, default='Chameleon', help='Camera Model Name')
    parser.add_argument('--pixelFormat',type=str,default='RGB10', help='Pixel format for camera')
    return parser

def ParseArgs():
    parser = CaseArgumentParser()
    args = parser.parse_args()
    return vars(args)

class DataType:
    npType = np.uint16
def color_transformation(matrixIn,rgbMatrix,rgb0matrix, npType, pixelFormat):
    def process_pixel(pixel, pixelFormat):
        matrixOut = np.dot(rgbMatrix, pixel).astype(npType)
        matrixOut = np.add(matrixOut,rgb0matrix).astype(npType)
        matrixOut = pixelFormat_conversion(matrixOut, pixelFormat).astype(npType)
        matrixOut=matrixOut.flatten()
        return matrixOut
    for row in range(matrixIn.shape[0]):
        for col in range(matrixIn.shape[1]):
            matrixIn[row, col] = process_pixel(matrixIn[row, col], pixelFormat)
    return matrixIn

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
def waitForTestTime(time_for_sleep):
    threadSleepSeconds = time_for_sleep
    print(f"Thread sleep for {threadSleepSeconds} seconds: ")
    for remaining in range(threadSleepSeconds, 0, -1):
        sys.stdout.write("\r")
        sys.stdout.write("{:2d} seconds remaining".format(remaining))
        sys.stdout.flush()
        time.sleep(1)
    sys.stdout.write("\rComplete!            \n")
    return threadSleepSeconds
class InputMatrices:
    colorBase = 'RGB'
    combination_list = []
    for col in colorBase:
        for col1 in colorBase:
            combination_list.append(col + col1)
    colorMatrix = np.array(combination_list).reshape(3, 3)
    rgbListZeros=[0 for i in range (len(combination_list))]
    rgbList=[1.0, 0.0, 0.0, 2.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    transformationMatrix = np.array(rgbList,dtype=DataType.npType).reshape(3, 3)
    rgbInMatrix = np.array([63, 126, 255],dtype=DataType.npType).reshape(1, 3)
class ResetMatrices:
    colorBase = 'RGB'
    colorBaseVal = [0.0,0.0,0.0]
    reset_color_base = ['RR','RG', 'RB', 'GR', 'GG','GB','BR','BG','BB']
    reset_color_base_val=[1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]

class MatrixSetter:
    colorBase = 'RGB'
    reset_color_base = ['RR', 'RG', 'RB', 'GR', 'GG', 'GB', 'BR', 'BG', 'BB']
    def resetMatricesToDefault(self, grabberHandle):
        for i in range(len(self.colorBase)):
            (status) = KYFG_SetGrabberValueFloat(grabberHandle, f"ColorTransformation{self.colorBase[i]}0",
                                                 ResetMatrices.colorBaseVal[i])
        for i in range(len(self.reset_color_base)):
            (status) = KYFG_SetGrabberValueFloat(grabberHandle, f"ColorTransformation{self.reset_color_base[i]}",
                                      ResetMatrices.reset_color_base_val[i])
        pass
    def setMatrixStartValue(self, grabberHandle):
        for i in range(len(self.colorBase)):
            (status) = KYFG_SetGrabberValueFloat(grabberHandle, f"ColorTransformation{self.colorBase[i]}0",
                                                 float(InputMatrices.rgbInMatrix[0][i]))
        for i in range(len(self.reset_color_base)):
            (status) = KYFG_SetGrabberValueFloat(grabberHandle, f"ColorTransformation{self.reset_color_base[i]}",
                                      float(InputMatrices.rgbListZeros[i]))
    def setColorTransformationMatrix(self,grabberHandle,RGB0Metrix,RGBMatrix):
        for i in range(len(self.colorBase)):
            (status) = KYFG_SetGrabberValueFloat(grabberHandle, f"ColorTransformation{self.colorBase[i]}0",
                                                 float(RGB0Metrix[i]))
        for i in range(len(self.reset_color_base)):
            (status) = KYFG_SetGrabberValueFloat(grabberHandle, f"ColorTransformation{self.reset_color_base[i]}",
                                      float(RGBMatrix[i]))
def printCurrentMatrices(grabberHandle):
    for i in range(len(MatrixSetter.colorBase)):
        (status, value) = KYFG_GetGrabberValueFloat(grabberHandle, f"ColorTransformation{MatrixSetter.colorBase[i]}0")
        print(f'{MatrixSetter.colorBase[i]}0 {value}')
    for i in range(len(MatrixSetter.reset_color_base)):
        (status, value) = KYFG_GetGrabberValueFloat(grabberHandle, f"ColorTransformation{MatrixSetter.reset_color_base[i]}")
        print(f'{MatrixSetter.reset_color_base[i]} {value}')
def pixelFormat_conversion(matrix, format):
    upper_threshold=255
    match format:
        case 'RGB8':upper_threshold = 255
        case 'RGB10': upper_threshold = 1023
        case 'RGB12': upper_threshold = 4095
        case 'RGB14': upper_threshold = 10000
        case 'RGB16': upper_threshold = 10000
    matrixOut=np.clip(matrix, a_min=0, a_max=upper_threshold)
    return matrixOut

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

    camera = args['camera']
    pixelFormat = args['pixelFormat']
    RGBColors = 3
    matrix_multiplier=1
    DataType.npType = np.uint16
    match pixelFormat:
        case 'RGB8':
            matrix_multiplier=1
            DataType.npType = np.uint8
        case 'RGB10': matrix_multiplier = 4
        case 'RGB12':matrix_multiplier = 16
        case 'RGB14':matrix_multiplier = 40
        case 'RGB16':matrix_multiplier = 40
        case _:
            print('Wrong pixel format. Only RGB')
            return CaseReturnCode.WRONG_PARAM_VALUE
    input_matrices=InputMatrices()
    input_matrices.rgbInMatrix=pixelFormat_conversion(input_matrices.rgbInMatrix*matrix_multiplier,pixelFormat)
    (grabberHandle,)=KYFG_Open(device_index)
    # Find camera from perimeters
    (status,cameraList)=KYFG_UpdateCameraList(grabberHandle)
    cameraHandle=0
    for cameraHan in cameraList:
        (status, camInfo) = KYFG_CameraInfo2(cameraHan)
        if camera in camInfo.deviceModelName:
            cameraHandle=cameraHan
            break
    if cameraHandle==0:
        print(f'There is no camera {camera} on this grabber')
        return CaseReturnCode.NO_HW_FOUND
    # Open camera
    (status,) = KYFG_CameraOpen2(cameraHandle,None)
    (status,) = KYFG_SetCameraValueEnum_ByValueName(cameraHandle, "PixelFormat", pixelFormat)
    (status,) = KYFG_SetGrabberValueInt(grabberHandle, "CameraSelector", cameraList.index(cameraHandle))
    MatrixSetter.resetMatricesToDefault(MatrixSetter(),grabberHandle)

    print('Color configuration for the first frame')
    printCurrentMatrices(grabberHandle)
    (status,) = KYFG_SetCameraValueEnum(cameraHandle, "VideoSourcePatternType", 6)
    # KYFG_SetCameraValueEnum(cameraHandle, "TestPattern", 512)
    (status, width) = KYFG_GetCameraValueInt(cameraHandle, "Width")
    (status, height) = KYFG_GetCameraValueInt(cameraHandle, "Height")
    (status, streamHandle) = KYFG_StreamCreateAndAlloc(cameraHandle, 16, 0)
    (status,) = KYFG_CameraStart(cameraHandle, streamHandle, 1)
    waitForTestTime(1)
    (status,) = KYFG_CameraStop(cameraHandle)
    (frame_size,) = KYFG_StreamGetSize(streamHandle)
    (Frame_pointer,) = KYFG_StreamGetPtr(streamHandle, 0)
    acquired_image = np.empty((height, width, RGBColors),
                              dtype=DataType.npType)  # numPy Image array initializatoion
    ctypes.memmove(acquired_image.ctypes.data, Frame_pointer, frame_size)
    transformed_image = color_transformation(acquired_image, input_matrices.transformationMatrix, input_matrices.rgbInMatrix, DataType.npType, pixelFormat)
    (status,) = KYFG_StreamDelete(streamHandle)
    waitForTestTime(3)
    MatrixSetter.setColorTransformationMatrix(MatrixSetter(), grabberHandle, input_matrices.rgbInMatrix.flatten(),
                                              input_matrices.rgbList)
    print('Color configuration for the second frame')
    printCurrentMatrices(grabberHandle)
    (status, newStreamHandle) = KYFG_StreamCreateAndAlloc(cameraHandle, 1, 0)
    (status,) = KYFG_CameraStart(cameraHandle, newStreamHandle, 1)
    waitForTestTime(1)
    (status,) = KYFG_CameraStop(cameraHandle)
    (frame_size,) = KYFG_StreamGetSize(newStreamHandle)
    (new_Frame_pointer,) = KYFG_StreamGetPtr(newStreamHandle, 0)
    new_acquired_image = np.empty((height, width, RGBColors),
                                  dtype=DataType.npType)  # numPy Image array initializatoion
    ctypes.memmove(new_acquired_image.ctypes.data, new_Frame_pointer, frame_size)
    (status,) = KYFG_StreamDelete(newStreamHandle)
    (status,) = KYFG_CameraClose(cameraHandle)
    MatrixSetter.resetMatricesToDefault(MatrixSetter(),grabberHandle)
    print('Color configuration in the end of the test')
    printCurrentMatrices(grabberHandle)
    assert (new_acquired_image == transformed_image).all(), 'Images are not equal'
    print('IMAGES ARE EQUAL')
    (status,) = KYFG_Close(grabberHandle)
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
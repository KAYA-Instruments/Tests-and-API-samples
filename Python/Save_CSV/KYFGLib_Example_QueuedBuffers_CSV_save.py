import sys
import os
sys.path.insert(0, os.environ['KAYA_VISION_POINT_PYTHON_PATH'])
import KYFGLib
from KYFGLib import *
import numpy as np



def numpy_from_data(buffData, buffSize, datatype):
    data_pointer = ctypes.cast(buffData, ctypes.c_char_p)
    buffer_from_memory = ctypes.pythonapi.PyMemoryView_FromMemory
    buffer_from_memory.restype = ctypes.py_object
    buffer = buffer_from_memory(data_pointer, buffSize)
    return np.frombuffer(buffer, datatype)

############################# Callback Function ##################################

# Example of user class containing stream information


class StreamInfoStruct:
    def __init__(self):
        self.width = 0
        self.height = 0
        self.data = []
        self.datatype = np.uint8
        self.callbackCount = 0

# Example of user Stream_callback_func function implementation
# Parameters brief:
#       buffHandle - API handle to received data. Type: STREAM_HANDLE
#       userContext - Retrieved when the callback is issued. Helps to determine the origin of stream in host application.
def Stream_callback_func(buffHandle, userContext): 

    if buffHandle == NULL_STREAM_BUFFER_HANDLE or buffHandle == INVALID_STREAM_BUFFER_HANDLE:
        Stream_callback_func.copyingDataFlag = 0
        return

    print('Good callback streams buffer handle: ' + str(format(int(buffHandle), '02x')), end='\r')

    '''
    print('buffer ' + str(format(buffHandle, '02x')) + ': height=' + str(userContext.height) + ', width=' + str(
        userContext.width) + ', callback count=' + str(userContext.callbackCount))
        userContext.callbackCount += 1
    '''

    # Example of retrieving buffer information
    (KYFG_BufferGetInfo_status, buffData, pInfoSize, pInfoType) = KYFG_BufferGetInfo(buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_BASE)
    (KYFG_BufferGetInfo_status, buffSize, pInfoSize, pInfoType) = KYFG_BufferGetInfo(buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_SIZE)
    #print("Buffer Info: Base " + str(pInfoBase) + ", Size " + str(pInfoSize) + ", Timestamp "+ str(pInfoTimestamp) + ", FPS " + str(pInfoFPS)
    #      + ", ID " + str(pInfoID), end='\r')

    sys.stdout.flush()
    userContext.data = numpy_from_data(buffData, buffSize, userContext.datatype)
    try:
        (KYFG_BufferToQueue_status,) = KYFG_BufferToQueue(buffHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
    except:
        pass
        # print("KYFG_BufferToQueue_status: " + str(format(KYFG_BufferToQueue_status, '02x')))
    Stream_callback_func.copyingDataFlag = 0
    return

Stream_callback_func.data = 0
Stream_callback_func.copyingDataFlag = 0

################################ Defines ###################################################

MAX_BOARDS = 4

fgHandleArray = [0 for i in range(MAX_BOARDS)]

detectedCameras = []

grabberIndex = 1

camHandleArray = [[0 for x in range(0)] for y in range(MAX_BOARDS)]

buffHandle = STREAM_HANDLE()

cameraStreamHandle = 0

frameDataSize = 0
frameDataAligment = 0

streamBufferHandle = [0 for i in range(16)]
streamAllignedBuffer = [0 for i in range(16)]

streamInfoStruct = StreamInfoStruct()

DEVICE_QUEUED_BUFFERS_SUPPORTED = "FW_Dma_Capable_QueuedBuffers_Imp"
################################## Control Functions ####################################
def printErr(err, msg = ""):
    print(msg)
    print("Error description: {0}".format(err))


def connectToGrabber(grabberIndex):
    global fgHandleArray
    (fghandle,) = KYFG_Open(grabberIndex)
    fgHandleArray[grabberIndex] = fghandle

    (status, tested_dev_info) = KYFGLib.KY_DeviceInfo(grabberIndex)
    print("Good connection to grabber " + str(grabberIndex) + ": " + tested_dev_info.szDeviceDisplayName + ", handle 0x" + str(format(int(fghandle), '02x')))
    
    (KYFG_GetGrabberValueInt_status, dmadQueuedBufferCapable) = KYFG_GetGrabberValueInt(fgHandleArray[grabberIndex], DEVICE_QUEUED_BUFFERS_SUPPORTED)

    if ( dmadQueuedBufferCapable != 1 ):
        print("grabber #" + str(grabberIndex) + " is not queued buffers capable\n")
        KYFG_Close(fghandle)
        fgHandleArray[grabberIndex] = 0
        return -1
    
    return 0


def startCamera (grabberIndex, cameraIndex):
    # put all buffers to input queue
    (KYFG_BufferQueueAll_status,) = KYFG_BufferQueueAll(cameraStreamHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_UNQUEUED, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
    print("KYFG_BufferQueueAll_status: " + str(format(KYFG_BufferQueueAll_status, '02x')))
    (KYFG_CameraStart_status,) = KYFG_CameraStart(camHandleArray[grabberIndex][cameraIndex], cameraStreamHandle, 0)
    print("KYFG_CameraStart_status: " + str(format(KYFG_CameraStart_status, '02x')))
    return 0

########################### Script ################################################


try:
    print("Welcome To KYFGLib Queued Buffers API Python Sample Script\n")

    initParams = KYFGLib_InitParameters()
    KYFGLib_Initialize(initParams)

    (KY_GetSoftwareVersion_status, soft_ver) = KY_GetSoftwareVersion()
    print("KYFGLib version: " + str(soft_ver.Major) + "." + str(soft_ver.Minor) + "." + str(soft_ver.SubMinor))
    if (soft_ver.Beta > 0):
        print("(Beta " + str(soft_ver.Beta) + ")")
    if (soft_ver.RC > 0):
        print("(RC " + str(soft_ver.RC) + ")")

    # Scan devices
    (status, fgAmount) = KYFGLib.KY_DeviceScan()
    if (status != FGSTATUS_OK):
        print("KY_DeviceScan() status: " + str(format(status, '02x')))

    # Print available devices params
    for x in range(fgAmount):
        (status, dev_info) = KYFGLib.KY_DeviceInfo(x)
        if (status != FGSTATUS_OK):
            print("Cant retrieve device #" + str(x) + " info")
            continue
        print("Device " + str(x) + ": " + dev_info.szDeviceDisplayName)
    
    c = 'x'
    while (c != 'e'):
        if (c != ''):
            print(
                "\nEnter choice: ([0-4]-select grabber) (o-open grabber) (c-connect to camera) (s-start) (t-stop) (e-exit) (i-info) (x-getXML) (k-save data to csv)")
        c = input("")
        if (len(c) != 1):
            print("Please enter one char")
            continue

        if (c >= '0' and c < str(MAXBOARDS)):
            grabberIndex = int(c)
            print("Selected grabber: " + str(c))
            print("\nGetting info about the grabber: ")
            (status, dev_info) = KY_DeviceInfo(grabberIndex)
            if (status != FGSTATUS_OK):
                print("Cant retrieve device #" + str(grabberIndex) + " info")
                continue
            print("DeviceDisplayName: " + dev_info.szDeviceDisplayName)
            print("Bus: " + str(dev_info.nBus))
            print("Slot: " + str(dev_info.nSlot))
            print("Function: " + str(dev_info.nFunction))
            print("DevicePID: 0x" + str(format(dev_info.DevicePID, '02x')))
            print("isVirtual: " + str(dev_info.isVirtual))

        elif (c == 'o'):
            connection = -1
            try:
                connection = connectToGrabber(grabberIndex)
            except KYException as err:
                print('\n')
                printErr(err, "Could not connect to grabber {0}".format(grabberIndex))

        elif (c == 's'):
            print('\r', end='')
            sys.stdout.flush()
            startCamera(grabberIndex, 0)

        elif (c == 't'):
            print('\r', end='')
            sys.stdout.flush()
            (CameraStop_status,) = KYFG_CameraStop(camHandleArray[grabberIndex][0])
            # print("CameraStop_status: " + str(format(CameraStop_status, '02x')))

        elif (c == 'k'):
            if len(streamInfoStruct.data) != 0:
                data = streamInfoStruct.data.reshape(streamInfoStruct.height, streamInfoStruct.width)
                np.savetxt("output.csv", data, delimiter=",", fmt="%d")
                print("Data saved to output.csv")
            else:
                print("No data to save!!")



        elif (c == 'c'):
            # scan for connected cameras
            (CameraScan_status, camHandleArray[grabberIndex]) = KYFG_UpdateCameraList(fgHandleArray[grabberIndex])
            print("Found " + str(len(camHandleArray[grabberIndex])) + " cameras")
            if(len(camHandleArray[grabberIndex]) == 0):
                print("Could not connect to a camera")
                continue

            # open a connection to chosen camera
            (KYFG_CameraOpen2_status,) = KYFG_CameraOpen2(camHandleArray[grabberIndex][0], None)
            # print("KYFG_CameraOpen2_status: " + str(format(KYFG_CameraOpen2_status, '02x')))
            if (KYFG_CameraOpen2_status == FGSTATUS_OK):
                print("Camera 0 was connected successfully")
            else:
                print("Something went wrong while opening camera")
                continue

            # Example of setting camera values
            (SetCameraValueInt_status_width,) = KYFG_SetCameraValueInt(camHandleArray[grabberIndex][0], "Width", 640)
            # print("SetCameraValueInt_status_width: " + str(format(SetCameraValueInt_status_width, '02x')))
            (SetCameraValueInt_status_height,) = KYFG_SetCameraValueInt(camHandleArray[grabberIndex][0], "Height", 480)
            # print("SetCameraValueInt_status_height: " + str(format(SetCameraValueInt_status_height, '02x')))
            #(SetCameraValueEnum_ByValueName_status,) = KYFG_SetCameraValueEnum_ByValueName(camHandleArray[grabberIndex][0], "PixelFormat", "Mono8")
            # print("SetCameraValueEnum_ByValueName_status: " + str(format(SetCameraValueEnum_ByValueName_status, '02x')))

            # Example of getting camera values
            (KYFG_GetValue_status, width) = KYFG_GetCameraValueInt(camHandleArray[grabberIndex][0], "Width")
            (KYFG_GetValue_status, height) = KYFG_GetCameraValueInt(camHandleArray[grabberIndex][0], "Height")
            (KYFG_GetValue_status, pixelFormat_int, pixelFormat) = KYFG_GetCameraValue(camHandleArray[grabberIndex][0], "PixelFormat")

            if pixelFormat.endswith('8'):
                streamInfoStruct.datatype = c_uint8
            else:
                streamInfoStruct.datatype = c_uint16
            streamInfoStruct.width = width
            streamInfoStruct.height = height

            # create stream and assign appropriate runtime acquisition callback function
            (KYFG_StreamCreate_status, cameraStreamHandle) = KYFG_StreamCreate(camHandleArray[grabberIndex][0], 0)
            # print("KYFG_StreamCreate_status: " + str(format(KYFG_StreamCreate_status, '02x')))

            # Register user 'Stream_callback_func' function and 'streamInfoStruct' as 'userContext'
            # 'streamInfoStruct' will be retrieved when the callback is issued
            (KYFG_StreamBufferCallbackRegister_status,) = KYFG_StreamBufferCallbackRegister(cameraStreamHandle,
                Stream_callback_func, streamInfoStruct)
            # print("KYFG_StreamBufferCallbackRegister_status: " + str(format(KYFG_StreamBufferCallbackRegister_status, '02x')))

            # Retrieve information about required frame buffer size and alignment
            (KYFG_StreamGetInfo_status, payload_size, frameDataSize, pInfoType) = \
                KYFG_StreamGetInfo(cameraStreamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_PAYLOAD_SIZE)

            (KYFG_StreamGetInfo_status, buf_allignment, frameDataAligment, pInfoType) = \
                KYFG_StreamGetInfo(cameraStreamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_BUF_ALIGNMENT)

            # allocate memory for desired number of frame buffers
            for iFrame in range(len(streamBufferHandle)):
                streamAllignedBuffer[iFrame] = aligned_array(buf_allignment, c_ubyte, payload_size)
                # print("Address of alligned array: " + hex(addressof(streamAllignedBuffer[iFrame])))
                (status, streamBufferHandle[iFrame]) = KYFG_BufferAnnounce(cameraStreamHandle,
                                                                           streamAllignedBuffer[iFrame], None)
        elif (c == 'i'):
            (Status, camInfo) = KYFG_CameraInfo2(camHandleArray[grabberIndex][0])
            print("master_link: ", str(camInfo.master_link))
            print("link_mask: ", str(camInfo.link_mask))
            print("link_speed: ", str(camInfo.link_speed))
            print("stream_id: ", str(camInfo.stream_id))
            print("deviceVersion: ", str(camInfo.deviceVersion))
            print("deviceVendorName: ", str(camInfo.deviceVendorName))
            print("deviceManufacturerInfo: ", str(camInfo.deviceManufacturerInfo))
            print("deviceModelName: ", str(camInfo.deviceModelName))
            print("deviceID: ", str(camInfo.deviceID))
            print("deviceUserID: ", str(camInfo.deviceUserID))
            print("outputCamera: ", str(camInfo.outputCamera))
            print("virtualCamera: ", str(camInfo.virtualCamera))
            print("deviceFirmwareVersion: ", str(camInfo.deviceFirmwareVersion))

        elif (c == 'x'):
            (KYFG_CameraGetXML_status, isZipped, buffer) = KYFG_CameraGetXML(camHandleArray[grabberIndex][0])
            print("Is Zipped: " + str(isZipped))
            # print("KYFG_CameraGetXML_status: " + str(format(KYFG_CameraGetXML_status, '02x')))
            if (isZipped == False):
                print("Writing buffer to xml file...")
                newFile = open("camera_xml.xml", "w")
                newFile.write(''.join(buffer))
                newFile.close()
            else:
                print("Writing buffer to zip file...")
                newFile = open("camera_xml.zip", "wb")
                newFile.write(bytes(buffer))
                newFile.close()
        else:
            print("Please enter a correct character")

    input("\nPress enter to exit")

    if (len(camHandleArray[grabberIndex]) > 0):
        (KYFG_CameraClose_status,) = KYFG_CameraClose(camHandleArray[grabberIndex][0])
        (CallbackRegister_status,) = KYFG_StreamBufferCallbackUnregister(cameraStreamHandle, Stream_callback_func)
    if (fgHandleArray[grabberIndex] != 0):
        (KYFG_Close_status,) = KYFG_Close(fgHandleArray[grabberIndex])


except KYException as KYe:
    print("KYException occurred: ")
    raise













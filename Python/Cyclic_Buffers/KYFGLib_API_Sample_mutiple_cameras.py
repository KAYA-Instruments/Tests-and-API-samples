import sys
import os
sys.path.insert(0, os.environ['KAYA_VISION_POINT_PYTHON_PATH'])
import KYFGLib
from KYFGLib import *

############################ Callback Detection ############################

def Device_event_callback_func(userContext, event):
    if (isinstance(event, KYDEVICE_EVENT_CAMERA_CONNECTION_LOST) == True):
        print("KYDEVICE_EVENT_CAMERA_CONNECTION_LOST_ID event recognized")
        print("event_id: " + str(event.deviceEvent.eventId))
        print("cam_handle: " + format(event.camHandle.get(), '02x'))   
        print("device_link: " + str(event.iDeviceLink))
        print("camera_link: " + str(event.iCameraLink))
    elif (isinstance(event, KYDEVICE_EVENT_CAMERA_START) == True):
        print("KYDEVICE_EVENT_CAMERA_START event recognized")
        print("event_id: " + str(event.deviceEvent.eventId))
        print("camHandle: " + format(event.camHandle.get(), '02x'))
    elif (isinstance(event, KYDEVICE_EVENT_SYSTEM_TEMPERATURE) == True):
        print("KYDEVICE_EVENT_SYSTEM_TEMPERATURE event recognized")
        print("event_id: " + str(event.deviceEvent.eventId))
        print("temperatureThresholdId: " + str(event.temperatureThresholdId))
    elif (isinstance(event, KYDEVICE_EVENT_CXP2_HEARTBEAT) == True):
        print("KYDEVICE_EVENT_CXP2_HEARTBEAT event recognized")
        print("event_id: " + str(event.deviceEvent.eventId))
        print("camHandle: " + format(event.camHandle.get(), '02x'))
    elif (isinstance(event, KYDEVICE_EVENT_CXP2_EVENT) == True):
        print("KYDEVICE_EVENT_CXP2_EVENT event recognized")
        print("event_id: " + str(event.deviceEvent.eventId))
        print("camHandle: " + format(event.camHandle.get(), '02x'))
    elif (isinstance(event, KYDEVICE_EVENT_GENCP_EVENT) == True):
        # event "KYDEVICE_EVENT_GENCP_EVENT" for CLHS
        print("KYDEVICE_EVENT_GENCP_EVENT event recognized")
        print("event_id: " + str(event.deviceEvent.eventId))
    elif (isinstance(event, KYDEVICE_EVENT_GIGE_EVENTDATA) == True):
        # event "KYDEVICE_EVENT_GIGE_EVENTDATA" for 10GigE
        print("KYDEVICE_EVENT_GIGE_EVENTDATA event recognized")
        print("event_id: " + str(event.deviceEvent.eventId))
    else:
        print("Unknown event recognized")


############################# Callback Function ##################################

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
    (KYFG_BufferGetInfo_status, pInfoBase, pInfoSize, pInfoType) = KYFG_BufferGetInfo(
         buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_BASE) # PTR
    (KYFG_BufferGetInfo_status, pInfoSize, pInfoSize, pInfoType) = KYFG_BufferGetInfo(
        buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_SIZE) # SIZET
    (KYFG_BufferGetInfo_status, pInfoPTR, pInfoSize, pInfoType) = KYFG_BufferGetInfo(
        buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_USER_PTR)  # PTR
    (KYFG_BufferGetInfo_status, pInfoTimestamp, pInfoSize, pInfoType) = KYFG_BufferGetInfo(
        buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_TIMESTAMP)  # UINT64
    (KYFG_BufferGetInfo_status, pInfoFPS, pInfoSize, pInfoType) = KYFG_BufferGetInfo(
        buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_INSTANTFPS)  # FLOAT64
    (KYFG_BufferGetInfo_status, pInfoID, pInfoSize, pInfoType) = KYFG_BufferGetInfo(
        buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_ID)  # UINT32
    #print("Buffer Info: Base " + str(pInfoBase) + ", Size " + str(pInfoSize) + ", Timestamp "+ str(pInfoTimestamp) + ", FPS " + str(pInfoFPS)
    #      + ", ID " + str(pInfoID), end='\r')
    
    if ( Stream_callback_func.copyingDataFlag == 0):
        Stream_callback_func.copyingDataFlag = 1
    
    sys.stdout.flush()
    Stream_callback_func.copyingDataFlag = 0
    return

Stream_callback_func.data = 0
Stream_callback_func.copyingDataFlag = 0

# Example of user class containing stream information
class StreamInfoStruct:
    def __init__(self):
        self.width = 640
        self.height = 480
        self.callbackCount = 0
        return

################################ Defines ###################################################

MAX_BOARDS = 4

fgHandleArray = [0 for i in range(MAX_BOARDS)]

detectedCameras = []

grabberIndex = 1

camHandleArray = [[0 for x in range(0)] for y in range(MAX_BOARDS)]

buffHandle = STREAM_HANDLE()

streamInfoStructArray = []

cameraStreamHandle_array = []

################################## Control Functions ####################################

def printErr(err, msg = ""):
    print(msg)
    print("Error description: {0}".format(err))


def connectToGrabber(grabberIndex):
    global fgHandleArray
    (fghandle,) = KYFG_Open(grabberIndex)
    fgHandleArray[grabberIndex] = fghandle

    (status, tested_dev_info) = KYFGLib.KY_DeviceInfo(grabberIndex)
    print("Good connection to grabber " + str(
        grabberIndex) + ": " + tested_dev_info.szDeviceDisplayName + ", handle 0x" + str(format(int(fghandle), '02x')))
    return 0


########################### Script ################################################
try:
    print("Welcome To KYFGLib API Python Sample Script\n")

    initParams = KYFGLib_InitParameters()
    # initParams. =
    KYFGLib_Initialize(initParams)

    (KY_GetSoftwareVersion_status, soft_ver) = KY_GetSoftwareVersion()
    print("KYFGLib version: " + str(soft_ver.Major) + "." + str(soft_ver.Minor) + "." + str(soft_ver.SubMinor))
    if (soft_ver.Beta > 0):
        print("(Beta " + str(soft_ver.Beta) + ")")
    if (soft_ver.RC > 0):
        print("(RC " + str(soft_ver.RC) + ")")

    # Scan for availible grabbers
    (KYFG_Scan_status, fgAmount) = KY_DeviceScan()
    if (KYFG_Scan_status != FGSTATUS_OK):
        print("KY_DeviceScan() status: " + str(format(KYFG_Scan_status, '02x')))

    # Print available grabbers params
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
                "\nEnter choice: ([0-4]-select grabber) (o-open grabber) (c-connect to camera)(s-start)(t-stop)(e-exit)(i-camera info)(x-getXML)")
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
            print("DevicePID: " + str(dev_info.DevicePID))
            print("isVirtual: " + str(dev_info.isVirtual))

        elif (c == 'c'):
            # scan for connected cameras
            (CameraScan_status, camHandleArray[grabberIndex]) = KYFG_UpdateCameraList(fgHandleArray[grabberIndex])
            print("Found " + str(len(camHandleArray[grabberIndex])) + " cameras");
            if (len(camHandleArray[grabberIndex]) == 0):
                print("Could not connect to a camera")
                continue

            # open a connection to all connected cameras
            for i in range(0, len(camHandleArray[grabberIndex])):
                (KYFG_CameraOpen2_status,) = KYFG_CameraOpen2(camHandleArray[grabberIndex][i], None)
                # print("KYFG_CameraOpen2_status: " + str(format(KYFG_CameraOpen2_status, '02x')))
                if (KYFG_CameraOpen2_status == FGSTATUS_OK):
                    print("Camera {} was connected successfully".format(i))
                else:
                    print("Something went wrong while opening camera")
                    continue

                # Example of setting and getting camera values
                (SetCameraValueInt_status_width,) = KYFG_SetCameraValueInt(camHandleArray[grabberIndex][i], "Width", 640)
                # print("SetCameraValueInt_status_width: " + str(format(SetCameraValueInt_status_width, '02x')))
                (SetCameraValueInt_status_height,) = KYFG_SetCameraValueInt(camHandleArray[grabberIndex][i], "Height", 480)
                # print("SetCameraValueInt_status_height: " + str(format(SetCameraValueInt_status_height, '02x')))
                # (SetCameraValueEnum_ByValueName_status,) = KYFG_SetCameraValueEnum_ByValueName(camHandleArray[grabberIndex][0], "PixelFormat", "Mono8")
                # print("SetCameraValueEnum_ByValueName_status: " + str(format(SetCameraValueEnum_ByValueName_status, '02x')))

                # Example of getting camera values
                (KYFG_GetValue_status, width) = KYFG_GetCameraValueInt(camHandleArray[grabberIndex][i], "Width")
                (KYFG_GetValue_status, height) = KYFG_GetCameraValueInt(camHandleArray[grabberIndex][i], "Height")

                cam_info_struct = StreamInfoStruct()
                cam_info_struct.width = width
                cam_info_struct.height = height
                streamInfoStructArray.append(cam_info_struct)

                # Set ROI Width
                '''
                (SetCameraValue_status_width,) = KYFG_SetCameraValue(camHandleArray[grabberIndex][i], "Width", 640)
                print("\nWidth SetCameraValue_status_width: " + str(format(SetCameraValue_status_width, '02x')))
                (GetCameraValueInt_status, width) = KYFG_GetCameraValue(camHandleArray[grabberIndex][i], "Width")
                print("Returned width: " + str(width))
                '''

                # Set ROI Height
                '''
                (SetCameraValue_status_height,) = KYFG_SetCameraValue(camHandleArray[grabberIndex][i], "Height", 480)
                print("\nSetCameraValueInt_status_height: " + str(format(SetCameraValue_status_height, '02x')))
                (GetCameraValueInt_status, height) = KYFG_GetCameraValue(camHandleArray[grabberIndex][i], "Height")
                print("Returned height: " + str(height))
                '''

                # Avaliable on cams with enabled PixelFormat parameter
                '''
                (SetCameraValue_status,) = KYFG_SetCameraValue(camHandleArray[grabberIndex][i], "PixelFormat", "Mono8")
                print("\nPixelFormat status1: " + str(format(SetCameraValue_status, '02x')))
                (SetCameraValue_status,) = KYFG_SetCameraValue(camHandleArray[grabberIndex][i], "PixelFormat", 17301505)
                print("PixelFormat status2: " + str(format(SetCameraValue_status, '02x')))
                (GetCameraValue_status, pixel_format_str, pixel_format_int) = KYFG_GetCameraValue(camHandleArray[grabberIndex][i], "PixelFormat")
                print("Returned PixelFormat: " + pixel_format_str + " : " + str(pixel_format_int))
                '''

                # Avaliable on cams with enabled BF_AutoLevelAdjust parameter
                '''
                (SetCameraValue_status,) = KYFG_SetCameraValue(camHandleArray[grabberIndex][i], "BF_AutoLevelAdjust", True);
                print("\nBF_AutoLevelAdjust SetCameraValue_status: " + str(format(SetCameraValue_status, '02x')))
                (GetCameraValue_status,auto_level) = KYFG_GetCameraValue(camHandleArray[grabberIndex][i], "BF_AutoLevelAdjust");
                print("Returned BF_AutoLevelAdjust value: " + str(auto_level))
                '''

                # Avaliable on cams with enabled ExposureTime parameter
                '''
                (SetCameraValue_status,) = KYFG_SetCameraValue(camHandleArray[grabberIndex][i], "ExposureTime", 25.84);
                print("\nExposureTime SetCameraValue_status: " + str(format(SetCameraValue_status, '02x')))
                (SetCameraValue_status, exposure_time) = KYFG_GetCameraValue(camHandleArray[grabberIndex][i], "ExposureTime");
                print("Returned Exposure Time: " + str(exposure_time))
                '''

                # Avaliable on cams with enabled DeviceUserID parameter
                '''
                (SetCameraValue_status,) = KYFG_SetCameraValue(camHandleArray[grabberIndex][i], "DeviceUserID", "Tester Name");
                print("\nDeviceUserID SetCameraValue_status: " + str(format(SetCameraValue_status, '02x')))
                (SetCameraValue_status, user_id) = KYFG_GetCameraValueStringCopy(camHandleArray[grabberIndex][i], "DeviceUserID");
                print("Returned DeviceUserID: " + user_id)
                '''

                # Avaliable on cams with enabled DeviceUserID parameter - Working on KAYA INSTRUMENTS 19HS
                '''
                (GetCameraValue_status, ex) = KYFG_GetCameraValue(camHandleArray[grabberIndex][i], "UserMemoryPageSave");
                print("Has UserMemoryPageSave been executed: " + str(ex) 
                (SetCameraValue_status,) = KYFG_SetCameraValue(camHandleArray[grabberIndex][i], "UserMemoryPageAll", bytes([2,3,4,5,6,7]));
                print("Setting  UserMemoryPageAll register status: " + str(format(SetCameraValue_status, '02x')))  
                (SetCameraValue_status,) = KYFG_SetCameraValue(camHandleArray[grabberIndex][i], "UserMemoryPageSave", 0);
                print("Saving UserMemoryPageAll status: " + str(format(SetCameraValue_status, '02x')))
                (GetCameraValue_status, buffer) = KYFG_GetCameraValue(camHandleArray[grabberIndex][i], "UserMemoryPageAll");
                print("Returned  UserMemoryPageAll register status: " + str(buffer))  
                (GetCameraValue_status, ex) = KYFG_GetCameraValue(camHandleArray[grabberIndex][i], "UserMemoryPageSave");
                print("Has UserMemoryPageSave been executed: " + str(ex))
                '''

                # create stream and assign appropriate runtime acquisition callback function
                (StreamCreateAndAlloc_status, cameraStreamHandle) = KYFG_StreamCreateAndAlloc(camHandleArray[grabberIndex][i], 16, 0)
                cameraStreamHandle_array.append(cameraStreamHandle)
                # print("StreamCreateAndAlloc_status: " + str(format(StreamCreateAndAlloc_status, '02x')))

                # Register user 'Stream_callback_func' function and 'streamInfoStruct' as 'userContext'
                # 'streamInfoStruct' will be retrieved when the callback is issued
                (CallbackRegister_status) = KYFG_StreamBufferCallbackRegister(cameraStreamHandle_array[i], Stream_callback_func,
                                                                              streamInfoStructArray[i])
                # print("KYFG_StreamBufferCallbackRegister_status: " + str(format(CallbackRegister_status, '02x')))

        elif (c == 's'):
            for i in range(0, len(camHandleArray[grabberIndex])):
                (CameraStart_status,) = KYFG_CameraStart(camHandleArray[grabberIndex][i], cameraStreamHandle_array[i], 0)
                # print("CameraStart_status: " + str(format(CameraStart_status, '02x')))

        elif (c == 'o'):
            connection = -1
            try:
                connection = connectToGrabber(grabberIndex)
            except KYException as err:
                print('\n')
                printErr(err, "Could not connect to grabber {0}".format(grabberIndex))
            if (connection == 0):
                (KYDeviceEventCallBackRegister_status,) = KYDeviceEventCallBackRegister(fgHandleArray[grabberIndex],
                                                                                        Device_event_callback_func, 0)

        elif (c == 't'):
            print('\r', end='')
            sys.stdout.flush()
            for i in range(0, len(camHandleArray[grabberIndex])):
                (CameraStop_status,) = KYFG_CameraStop(camHandleArray[grabberIndex][i])
                # print("CameraStop_status: " + str(format(CameraStop_status, '02x')))

        elif (c == 'i'):
            for i in range(0, len(camHandleArray[grabberIndex])):
                (Status, camInfo) = KYFG_CameraInfo2(camHandleArray[grabberIndex][i])
                print("\nGetting info about camera no. {}: ".format(i))
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
            for i in range(0, len(camHandleArray[grabberIndex])):
                print("\nRetrieving XML from camera no. {}: ".format(i))
                (KYFG_CameraGetXML_status, isZipped, buffer) = KYFG_CameraGetXML(camHandleArray[grabberIndex][i])
                print("Is Zipped: " + str(isZipped))
                # print("KYFG_CameraGetXML_status: " + str(format(KYFG_CameraGetXML_status, '02x')))
                if (isZipped == False):
                    print("Writing buffer to xml file...")
                    newFile = open("camera_{}_xml.xml".format(i), "w")
                    newFile.write(''.join(buffer))
                    newFile.close()
                else:
                    print("Writing buffer to zip file...")
                    newFile = open("camera_{}_xml.zip".format(i), "wb")
                    newFile.write(bytes(buffer))
                    newFile.close()

        else:
            print("Please enter a correct character")

    input("\nPress enter to exit")

    if (len(camHandleArray[grabberIndex]) > 0):
        for i in range(0, len(camHandleArray[grabberIndex])):
            (KYFG_CameraClose_status,) = KYFG_CameraClose(camHandleArray[grabberIndex][i])
            (CallbackRegister_status,) = KYFG_StreamBufferCallbackUnregister(cameraStreamHandle_array[i], Stream_callback_func)
    if (fgHandleArray[grabberIndex] != 0):
        (KYFG_Close_status,) = KYFG_Close(fgHandleArray[grabberIndex])


except KYException as KYe:
    print("KYException occurred: ")
    raise

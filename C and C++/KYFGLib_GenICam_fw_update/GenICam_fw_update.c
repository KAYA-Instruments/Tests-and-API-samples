/************************************************************************ 
*    File: KYFGLib_Example.cpp
*    GenICam firmware update utility
*
*    KAYA Instruments Ltd.
*************************************************************************/

#include "stdafx.h"
#include "KYFGLib.h"

#if !defined(_countof)
#define _countof(_Array) (sizeof(_Array) / sizeof(_Array[0]))
#endif

#ifndef MIN
#define MIN(a,b) ((a) > (b) ? (b) : (a))
#endif
#ifndef MAX
#define MAX(a,b) ((a) > (b) ? (a) : (b))
#endif

#define VESION_MAJOR    2
#define VESION_MINOR    2

#define MAXBOARDS 4
FGHANDLE handle[MAXBOARDS];
int nKayaDevicesCount = 0;

FILE* log_file = NULL;
#define log_create(currentTime)\
    char log_file_name [MAX_PATH] = {"GenICam_fw_update_"};\
    strcat(log_file_name, currentTime);\
    strcat(log_file_name, ".log");\
    log_file = fopen((const char*)log_file_name, "w");

#define log_close()\
    if(log_file)\
    {\
        fclose(log_file);\
        log_file = NULL;\
    }

#define log_print(...)\
    printf(__VA_ARGS__);\
    if(log_file)\
        fprintf(log_file, __VA_ARGS__);

int ConnectToGrabber(unsigned int grabberIndex)
{
    if ((handle[grabberIndex] = KYFG_Open(grabberIndex)) != -1) // Connect to selected device
    {
        log_print("Good connection to grabber #%d, handle=%X\n", grabberIndex, handle[grabberIndex] );
        return 0;
    }
    else
    {
        log_print("Could not connect to grabber #%d\n", grabberIndex);
        fflush(stdin);
        getchar();
        return -1;
    }
}

const char* FW_UPDATE_FILE_SELECTOR = "FileSelector";
const char* FW_UPDATE_FILE_OPEN_MODE = "FileOpenMode";
const char* FW_UPDATE_FILE_OPERATION_SELECTOR = "FileOperationSelector";
const char* FW_UPDATE_FILE_OPERATION_STATUS = "FileOperationStatus";
const char* FW_UPDATE_FILE_OPERATION_RESULT = "FileOperationResult";
const char* FW_UPDATE_FILE_ACCESS_BUFFER = "FileAccessBuffer";
const char* FW_UPDATE_FILE_ACCESS_OFFSET = "FileAccessOffset";
const char* FW_UPDATE_FILE_ACCESS_LENGTH = "FileAccessLength";
const char* FW_UPDATE_FILE_OPERATION_EXECUTE = "FileOperationExecute";
const char* FW_UPDATE_DEVICE_RESET = "DeviceReset";

typedef enum {
    CHECK_FILE_MODE_COMPLETE_FILE = 0, // write complete file, then check.
    CHECK_FILE_MODE_PREV_SECTION = 1, // write file section and check previouse section
}CHECK_FILE_MODE;

typedef enum {
    UPDATE_FILE_MODE_WRITE_AND_CHECK = 0, // write file and check result
    UPDATE_FILE_MODE_WRITE_ONLY = 1, // write file only
    UPDATE_FILE_MODE_CHECK_ONLY = 2, // check file only
    UPDATE_FILE_MODE_WRITE_FIRST_SECTION_LAST = 3, // write the last file section last
}UPDATE_FILE_MODE;

UPDATE_FILE_MODE updateFileMode = UPDATE_FILE_MODE_WRITE_FIRST_SECTION_LAST;
CHECK_FILE_MODE checkFileMode = CHECK_FILE_MODE_COMPLETE_FILE;

void PrintBufferRange(uint8_t* buffer, int64_t startIdx, int64_t endIdx)
{
    if(startIdx > endIdx)
    {
        log_print("Incorrect indexes\n");
        return;
    }

    for(startIdx; startIdx <= endIdx; startIdx++)
    {
        log_print("%02x ", *(buffer + startIdx));
    }

    return;
}

void ExitFirmwareUpdate(int grabberIndex)
{
    log_print("\nExiting...\n");

    if(KYFG_Close(handle[grabberIndex]) != FGSTATUS_OK) // Close the selected device and unregisters all associated routines
    {
        log_print("Wasn't able to close grabber #%d\n", grabberIndex);
    }

    log_print("Press [enter] to exit");

    log_close();

    fflush(stdin);
    getchar();

    exit(-1);
}

int fw_checkChuckValid(CAMHANDLE camHandle, uint8_t* pFwUpdateBuffer, uint32_t accessBufferSize, int64_t offsetAddr, int64_t offsetSize)
{
    static uint8_t* pReadFwUpdateBuffer = NULL;
    pReadFwUpdateBuffer = (uint8_t*)realloc(pReadFwUpdateBuffer, accessBufferSize);

    int64_t prevChunkTestOffsetAddr = offsetAddr; // Current 
    KYFG_SetCameraValueInt(camHandle, FW_UPDATE_FILE_ACCESS_OFFSET, prevChunkTestOffsetAddr);
    KYFG_SetCameraValueInt(camHandle, FW_UPDATE_FILE_ACCESS_LENGTH, offsetSize);
    KYFG_SetCameraValueEnum_ByValueName(camHandle, FW_UPDATE_FILE_OPERATION_SELECTOR, "Read");
    KYFG_CameraExecuteCommand(camHandle, FW_UPDATE_FILE_OPERATION_EXECUTE);
    KYFG_GetCameraValue(camHandle, FW_UPDATE_FILE_ACCESS_BUFFER, pReadFwUpdateBuffer);

    if (memcmp(pFwUpdateBuffer, pReadFwUpdateBuffer, offsetSize) != 0)
    {
        log_print("\n\r Firmware Validation chunk error. Offset: %" PRId64 "\n\r", prevChunkTestOffsetAddr);
        log_print("\n\raccessBufferSize: %" PRIu32, accessBufferSize);
        log_print("\n\roffsetSize: %" PRId64, offsetSize);
        log_print("\n\rpFwUpdateBuffer chunk: \n\r");
        PrintBufferRange(pFwUpdateBuffer, 0, offsetSize - 1);
        log_print("\n\rpReadFwBuffer chunk: \n\r");
        PrintBufferRange(pReadFwUpdateBuffer, 0, offsetSize - 1);
        return -1;
    }
    return 0;
}

int fw_loadFile(CAMHANDLE camHandle, uint8_t* pFwUpdateBuffer, int64_t fwUpdateFileSizeTotal, uint32_t accessBufferSize, int64_t initialOffsetAddr)
{
    int res_fw_checkLastChuckValid = 0;
    char fileOperationStatus[256] = { 0 };
    uint32_t fileOperationStatusSize = sizeof(fileOperationStatus);
    int64_t offsetAddr = initialOffsetAddr;
    int64_t fwUpdateFileSize = fwUpdateFileSizeTotal;

    int64_t offsetSize = 0;
    while (fwUpdateFileSize > 0)
    {
        offsetSize = MIN(accessBufferSize, fwUpdateFileSize);

        if ((UPDATE_FILE_MODE_WRITE_AND_CHECK == updateFileMode)
            ||
            (UPDATE_FILE_MODE_WRITE_ONLY == updateFileMode)
            ||
            (UPDATE_FILE_MODE_WRITE_FIRST_SECTION_LAST == updateFileMode)
            )
        {
            // write value to buffer
            KYFG_SetCameraValue(camHandle, FW_UPDATE_FILE_ACCESS_BUFFER, pFwUpdateBuffer); // Send file buffer data to camera

            KYFG_SetCameraValueInt(camHandle, FW_UPDATE_FILE_ACCESS_OFFSET, offsetAddr); // Update file address
            KYFG_SetCameraValueInt(camHandle, FW_UPDATE_FILE_ACCESS_LENGTH, offsetSize); // Update file size

            KYFG_SetCameraValueEnum_ByValueName(camHandle, FW_UPDATE_FILE_OPERATION_SELECTOR, "Write"); // Set command to Write operation

            KYFG_CameraExecuteCommand(camHandle, FW_UPDATE_FILE_OPERATION_EXECUTE); // Execute Write operation

            KYFG_GetCameraValueStringCopy(camHandle, FW_UPDATE_FILE_OPERATION_STATUS, fileOperationStatus, &fileOperationStatusSize);

            if (0 != strcmp(fileOperationStatus, "Success"))
            {
                log_print("\n\r Firmware update error. Please try again!\n\r");
                break;
            }
        }

        if (
            (CHECK_FILE_MODE_PREV_SECTION == checkFileMode)
            &&
            ((UPDATE_FILE_MODE_WRITE_AND_CHECK == updateFileMode) || (UPDATE_FILE_MODE_CHECK_ONLY == updateFileMode) || (UPDATE_FILE_MODE_WRITE_FIRST_SECTION_LAST == updateFileMode))
            )
        {
            // Test previous chunk
            if (initialOffsetAddr != offsetAddr) // Check not first file data block
            {
                res_fw_checkLastChuckValid = fw_checkChuckValid(camHandle, pFwUpdateBuffer - accessBufferSize, accessBufferSize, offsetAddr - accessBufferSize, accessBufferSize); // OffsetSize is always accessBufferSize for non-final data chuck
                if (0 != res_fw_checkLastChuckValid)
                {
                    break;
                }
            }
        }

        // End of test of past 
        log_print("\rResult of Write operation to address 0x%" PRIx64 " is: %s. Complete:%" PRId64 " %%    ", offsetAddr, fileOperationStatus, (offsetAddr + offsetSize - initialOffsetAddr) * 100 / fwUpdateFileSizeTotal);

        fwUpdateFileSize -= offsetSize;
        offsetAddr += offsetSize;
        pFwUpdateBuffer += offsetSize;
    }

    // CHECK_FILE_MODE_PREV_SECTION == checkFileMode
    if ((0 == res_fw_checkLastChuckValid) && (CHECK_FILE_MODE_PREV_SECTION == checkFileMode) && (UPDATE_FILE_MODE_WRITE_ONLY != updateFileMode))
    {
        res_fw_checkLastChuckValid = fw_checkChuckValid(camHandle, pFwUpdateBuffer - offsetSize, accessBufferSize, offsetAddr - offsetSize, offsetSize); // Check last file data block
    }
    
    return res_fw_checkLastChuckValid;
}

int fw_checkCompletefile(CAMHANDLE camHandle, uint8_t* pFwUpdateBuffer, int64_t fwUpdateFileSizeTotal, uint32_t accessBufferSize, int64_t initialOffsetAddr)
{
    int res_fw_checkLastChuckValid = 0;
    int64_t fwUpdateFileSize = fwUpdateFileSizeTotal;
    int64_t offsetAddr = initialOffsetAddr;
    int64_t offsetSize = 0;

    log_print("\n\n\rFile validation: \n\r");

    while (fwUpdateFileSize > 0)
    {
        offsetSize = MIN(accessBufferSize, fwUpdateFileSize);
        res_fw_checkLastChuckValid = fw_checkChuckValid(camHandle, pFwUpdateBuffer, accessBufferSize, offsetAddr, offsetSize);
        if (0 != res_fw_checkLastChuckValid)
        {
            break;
        }

        log_print("\rResult of check operation of address 0x%" PRIx64 " complete:%" PRId64 " %%    ", offsetAddr, (offsetAddr + offsetSize - initialOffsetAddr) * 100 / fwUpdateFileSizeTotal);

        fwUpdateFileSize -= offsetSize;
        offsetAddr += offsetSize;
        pFwUpdateBuffer += offsetSize;
    }

    log_print("\n\n\r");

    return res_fw_checkLastChuckValid;
}

#define ASSERT_FGSTATUS(_func_) if(FGSTATUS_OK != _func_) {return -1;}

int fw_openFile(CAMHANDLE camHandle)
{
    ASSERT_FGSTATUS(KYFG_SetCameraValueEnum_ByValueName(camHandle, FW_UPDATE_FILE_SELECTOR, "FirmwareUpdate"));
    ASSERT_FGSTATUS(KYFG_SetCameraValueEnum_ByValueName(camHandle, FW_UPDATE_FILE_OPEN_MODE, "ReadWrite"));
    ASSERT_FGSTATUS(KYFG_SetCameraValueEnum_ByValueName(camHandle, FW_UPDATE_FILE_OPERATION_SELECTOR, "Open"));

    ASSERT_FGSTATUS(KYFG_CameraExecuteCommand(camHandle, FW_UPDATE_FILE_OPERATION_EXECUTE));

    char fileOperationStatus[256] = { 0 };
    uint32_t fileOperationStatusSize = sizeof(fileOperationStatus);

    ASSERT_FGSTATUS(KYFG_GetCameraValueStringCopy(camHandle, FW_UPDATE_FILE_OPERATION_STATUS, fileOperationStatus, &fileOperationStatusSize));
    log_print("Result of Open operation is: %s\n\r", fileOperationStatus);

    // Check successful open operation
    if (0 != strcmp(fileOperationStatus, "Success"))
    {
        return - 1;
    }
    return 0;
}

int fw_closeFile(CAMHANDLE camHandle)
{
    char fileOperationStatus[256] = { 0 };
    uint32_t fileOperationStatusSize = sizeof(fileOperationStatus);
    
    KYFG_SetCameraValueEnum_ByValueName(camHandle, FW_UPDATE_FILE_OPERATION_SELECTOR, "Close");
    KYFG_CameraExecuteCommand(camHandle, FW_UPDATE_FILE_OPERATION_EXECUTE);

    KYFG_GetCameraValueStringCopy(camHandle, FW_UPDATE_FILE_OPERATION_STATUS, fileOperationStatus, &fileOperationStatusSize);
    log_print("Result of Close operation is: %s\n\r", fileOperationStatus);

    return 0;
}

int main(int argc, char* argv[])
{
    int grabberIndex = 0, cameraIndex = 0;
    STREAM_HANDLE streamHandle = 0;
    CAMHANDLE camHandleArray[MAXBOARDS][KY_MAX_CAMERAS]; // There are maximum KY_MAX_CAMERAS cameras
    int detectedCameras[MAXBOARDS];
    char c = 0;

    time_t timeRaw;
    struct tm *timeInfo;
    time(&timeRaw);
    timeInfo = localtime(&timeRaw);
    char timeString[MAX_PATH] = {0};
    strftime(timeString, sizeof(timeString), "%Y.%m.%d_%H-%M-%S", timeInfo);
    log_create(timeString)

    log_print("GenICam firmware update. Version: %d.%d-" __TIMESTAMP__ "\n\r", VESION_MAJOR, VESION_MINOR);
    log_print("Log time: %s\n\n\r", timeString);

    KY_DeviceScan(&nKayaDevicesCount); // First scan for device to retrieve the number of virtual and hardware devices connected to PC
    log_print("Number of scan results: %d\n\r", nKayaDevicesCount);
    
    for(int i = 0; i < nKayaDevicesCount; i++)
    {
        log_print("Device %d: ", i);
        log_print("%s\n",KY_DeviceDisplayName(i)); // Show assigned name to each pid
    }

    static const int sGrabberIndexArgIndex = 1;
    static const int sCameraIndexArgIndex = 2;
    static const int sFirmwareUpdatePathArgIndex = 3;
    static const int sUpdateFileModeArgIndex = 4;
    static const int sCheckFileModeArgIndex = 5;
    
    // Read the input arguments
    if (argc <= sGrabberIndexArgIndex)
    {
        log_print("No Frame Grabber index specified\n\r");
        ExitFirmwareUpdate(grabberIndex);
    }
    else if (argc <= sCameraIndexArgIndex)
    {
        log_print("No Camera index specified\n\r");
        ExitFirmwareUpdate(grabberIndex);
    }
    else if (argc <= sFirmwareUpdatePathArgIndex)
    {
        log_print("No firmware update file was specified\n\r");
        ExitFirmwareUpdate(grabberIndex);
    }

    if (argc > sUpdateFileModeArgIndex)
    {
        updateFileMode = (UPDATE_FILE_MODE)argv[sUpdateFileModeArgIndex][0] - '0';
    }

    if (argc > sCheckFileModeArgIndex)
    {
        checkFileMode = (CHECK_FILE_MODE)argv[sCheckFileModeArgIndex][0] - '0';
    }

    log_print("updateFileMode=%d, checkFileMode=%d\n\r", updateFileMode, checkFileMode);

    grabberIndex = argv[sGrabberIndexArgIndex][0] - '0';
    log_print("Selected grabber #%d\n", grabberIndex);
    ConnectToGrabber(grabberIndex);

    KYFG_SetGrabberValueInt(handle[grabberIndex], "CameraDiscoveryDelay", 5000);

    detectedCameras[grabberIndex] = KY_MAX_CAMERAS;
    
    // Scan for connected cameras
    if(FGSTATUS_OK != KYFG_UpdateCameraList(handle[grabberIndex], camHandleArray[grabberIndex], &detectedCameras[grabberIndex]))
    {
        ExitFirmwareUpdate(grabberIndex);
    }

    log_print("Found %d cameras.\n", detectedCameras[grabberIndex]);

    cameraIndex = argv[sCameraIndexArgIndex][0] - '0';

    CAMHANDLE camHandle = camHandleArray[grabberIndex][cameraIndex];
    
    // Open a connection to chosen camera
    if(FGSTATUS_OK == KYFG_CameraOpen2(camHandle, 0))
    {
        log_print("Camera %d was connected successfully\n\r", cameraIndex);
        KYFGCAMERA_INFO2 cameraInfo;
        cameraInfo.version = 0;
        KYFG_CameraInfo2(camHandle, &cameraInfo);
        log_print("Vendor name\t\t: %s\n\r", cameraInfo.deviceVendorName);
        log_print("Model\t\t\t: %s\n\r", cameraInfo.deviceModelName);
        char deviceFirmwareVersion[32] = {0};
        uint32_t deviceFirmwareVersionSize = sizeof(deviceFirmwareVersion);
        KYFG_GetCameraValueStringCopy(camHandle, "DeviceFirmwareVersion", deviceFirmwareVersion, &deviceFirmwareVersionSize);
        log_print("Firmware Version\t: %s\n\r", deviceFirmwareVersion);
    }
    else
    {
        log_print("Camera isn't connected\n");
        ExitFirmwareUpdate(grabberIndex);
    }

    // Change camera speed to 3.125Gbps for more stable connection
    KYFG_SetCameraValueInt(camHandleArray[grabberIndex][cameraIndex], "ConnectionConfig", 0x10038);

    log_print("Input firmware update file path: '%s'\n\r", argv[sFirmwareUpdatePathArgIndex]);

    FILE* fwUpdateFile = fopen(argv[sFirmwareUpdatePathArgIndex], "rb");
    if (!fwUpdateFile)
    {
#ifdef __linux__
        char cwd[PATH_MAX] = {0};
        getcwd(cwd, sizeof(cwd));
        log_print("Firmware update file failed to open with error: '%s'! cwd=%s\n\r", strerror(errno), cwd);
#else
        log_print("Firmware update file failed to open with error %d!\n\r", GetLastError());
#endif
        ExitFirmwareUpdate(grabberIndex);
    }

    // Obtain file size:
    fseek(fwUpdateFile, 0, SEEK_END);
    long fwUpdateFileSizeTotal = ftell(fwUpdateFile);
    rewind(fwUpdateFile);

    if (0 != fw_openFile(camHandle))
    {
        ExitFirmwareUpdate(grabberIndex);
    }
    
    uint32_t accessBufferSize = 0;
    KYFG_GetCameraValueRegister(camHandle, FW_UPDATE_FILE_ACCESS_BUFFER, NULL, &accessBufferSize);
    if (accessBufferSize > 0)
    {
        log_print("Found that %s is of size: %" PRIu32 "\n\r", FW_UPDATE_FILE_ACCESS_BUFFER, accessBufferSize);
    }
    else
    {
        log_print("%s is wrong size: %" PRIu32 "\n\r", FW_UPDATE_FILE_ACCESS_BUFFER, accessBufferSize);
        ExitFirmwareUpdate(grabberIndex);
    }

    char fileOperationStatus[256] = { 0 };
    uint32_t fileOperationStatusSize = sizeof(fileOperationStatus);

    int64_t fwUpdateFileSize = (int64_t)fwUpdateFileSizeTotal;
    int res_fw_checkLastChuckValid = 0;
    static const int64_t sInitialOffsetChunk = 65536;
    int64_t initialOffsetAddr = 0;
    
    // Read the firmware update file and assign initial offset
    uint8_t* pFwUpdateBufferBase = (uint8_t*)malloc(fwUpdateFileSizeTotal + accessBufferSize);
    fread(pFwUpdateBufferBase, 1, fwUpdateFileSizeTotal, fwUpdateFile);
    uint8_t* pFwUpdateBuffer = pFwUpdateBufferBase;
    
    // UPDATE_FILE_MODE_WRITE_FIRST_SECTION_LAST == updateFileMode
    if (UPDATE_FILE_MODE_WRITE_FIRST_SECTION_LAST == updateFileMode)
    {
        // Update initial file pointer to skip the first section by sInitialOffsetChunk
        initialOffsetAddr = sInitialOffsetChunk;
        fwUpdateFileSize -= sInitialOffsetChunk;
        pFwUpdateBuffer += sInitialOffsetChunk;

        // Initialize first firmware section with 0's
        uint8_t* pFwUpdateBufferFirstChunk = (uint8_t*)malloc(accessBufferSize);
        memset(pFwUpdateBufferFirstChunk, 0, accessBufferSize);
        res_fw_checkLastChuckValid = fw_loadFile(camHandle, pFwUpdateBufferFirstChunk, accessBufferSize, accessBufferSize, 0);
        free(pFwUpdateBufferFirstChunk);

        if(0 != res_fw_checkLastChuckValid)
        {
            log_print("\n\r Failed to reset first firmware update section. Please try again!\n\r");
            ExitFirmwareUpdate(grabberIndex);
        }
    }
    // Load the rest of the file
    res_fw_checkLastChuckValid = fw_loadFile(camHandle, pFwUpdateBuffer, fwUpdateFileSize, accessBufferSize, initialOffsetAddr);

    // CHECK_FILE_MODE_COMPLETE_FILE == checkFileMode
    if ((0 == res_fw_checkLastChuckValid) // Check that there was no error before
        &&
        (UPDATE_FILE_MODE_WRITE_ONLY != updateFileMode)
        &&
        (CHECK_FILE_MODE_COMPLETE_FILE == checkFileMode)
        )
    {
        res_fw_checkLastChuckValid = fw_checkCompletefile(camHandle, pFwUpdateBuffer, fwUpdateFileSize, accessBufferSize, initialOffsetAddr);
    }

    // UPDATE_FILE_MODE_WRITE_FIRST_SECTION_LAST == updateFileMode
    if (UPDATE_FILE_MODE_WRITE_FIRST_SECTION_LAST == updateFileMode)
    {
        initialOffsetAddr = 0;
        fwUpdateFileSize = sInitialOffsetChunk;
        pFwUpdateBuffer = pFwUpdateBufferBase;

        res_fw_checkLastChuckValid = fw_loadFile(camHandle, pFwUpdateBuffer, fwUpdateFileSize, accessBufferSize, initialOffsetAddr);
        
        if(0 != res_fw_checkLastChuckValid)
        {
            log_print("\n\r Failed to write first firmware update section. Please try again!\n\r");
            ExitFirmwareUpdate(grabberIndex);
        }

        res_fw_checkLastChuckValid = fw_checkCompletefile(camHandle, pFwUpdateBuffer, fwUpdateFileSize, accessBufferSize, 0);
        
        fwUpdateFileSize = 0;
    }

    // Check all firmware was uploaded
    if ((0 == fwUpdateFileSize ) && (0 == res_fw_checkLastChuckValid)) // Finished uploading firmware update file
    {
        fw_closeFile(camHandle);

        log_print("\n\n\r ############################################################ \n\n\r");
        log_print("Firmware update was completed SUCCESSFULLY !!! \n\n\r");

        if (FGSTATUS_OK == KYFG_CameraExecuteCommand(camHandle, FW_UPDATE_DEVICE_RESET))
        {
            int firmwareUpdateWaitCount = 30;

            do{
                log_print("Wait for camera to finish update: %2d seconds    \r", firmwareUpdateWaitCount);
                Sleep(1000);
            }
            while(firmwareUpdateWaitCount-- > 0);

            log_print("\n\n\r");
        }
        else
        {
            log_print("Disconnect camera, power it and wait for 30 seconds for firmware update to finish\n\n\r");
        }
    }
    else
    {
        fw_closeFile(camHandle);
        log_print("############################################################ \n\r\n\r");
        log_print("Firmware update has FAILED !!! \n\r");
    }

    ExitFirmwareUpdate(grabberIndex);

    return 0;
}


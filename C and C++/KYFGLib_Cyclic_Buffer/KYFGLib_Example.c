/************************************************************************ 
*   File: KYFGLib_Example.c
*   Sample Frame Grabber API application
*
*   KAYA Instruments Ltd.
*************************************************************************/

#include "stdafx.h"

#include "KYFGLib.h"

#if !defined(_countof)
#define _countof(_Array) (sizeof(_Array) / sizeof(_Array[0]))
#endif

#ifdef _MSC_VER
#define PRISIZET "Iu" //https://msdn.microsoft.com/en-us/library/tcxf1dw6%28v=vs.110%29.aspx
#else
#define PRISIZET "zu"
#endif

#ifdef __GNUC__ // _aligned_malloc() implementation for gcc
void* _aligned_malloc(size_t size, size_t alignment)
{
    size_t pageAlign = size % 4096;
    if (pageAlign)
    {
        size += 4096 - pageAlign;
    }

    #if(GCC_VERSION <= 40407)
    void * memptr = 0;
    posix_memalign(&memptr, alignment, size);
    return memptr;
    #else
    return aligned_alloc(alignment, size);
    #endif
}
#endif // #ifdef __GNUC__

// Helper functions to get user input
char BlockingInput()
{
    char c = -1;
#ifdef _MSC_VER
    while (scanf_s(" %c", &c, (unsigned int)(sizeof(char))) == -1);
#else
    while ((c == -1) || (c == '\n'))
    {
        c = getc(stdin);
    }
#endif
    return c;
}

void CharInput(char expected_char, const char* error_str)
{
    int valid = 0;
    char c;

    while(!valid)
    {
        c = BlockingInput();

        valid = expected_char == c;

        if(!valid)
        {
            printf("%s", error_str);
        }
        else
        {
            break;
        }
    }
}

void NumberInRangeInput(int min, int max, int* value, const char* error_str)
{
    int valid = 0;
    char c;

    while(!valid)
    {
        c = BlockingInput();

        *value = c - '0';

        valid = *value >= min && *value <= max;

        if(!valid)
        {
            printf("%s", error_str);
        }
        else
        {
            break;
        }
    }
}

#define MINIMAL_CALLBACK // Comment out to obtain and print more information about each frame
void Stream_callback_func(STREAM_BUFFER_HANDLE streamBufferHandle, void* userContext)
{
    unsigned char* pFrameMemory = 0;
    uint32_t frameId = 0;
    #ifndef MINIMAL_CALLBACK
    size_t bufferSize = 0;
    void* pUserContext;
    uint64_t timeStamp;
    double instantFps;
    #endif
    userContext; // Suppress warning

    if(!streamBufferHandle)
    {
        // This callback indicates that acquisition has stopped
        return;
    }

    // As a minimum, application may want to get pointer to current frame memory and/or its numerical ID
    KYFG_BufferGetInfo(streamBufferHandle,
                       KY_STREAM_BUFFER_INFO_BASE,
                       &pFrameMemory,
                       NULL,
                       NULL);
    KYFG_BufferGetInfo(streamBufferHandle,
                       KY_STREAM_BUFFER_INFO_ID,
                       &frameId,
                       NULL,
                       NULL);

    printf(//"\n" // Uncomment to print on new line each time
           "\rGood callback stream's buffer handle:%" PRISTREAM_BUFFER_HANDLE ", ID:%02" PRIu32, streamBufferHandle, frameId);

    // Additionaly the following information can be obtained:
    #ifndef MINIMAL_CALLBACK
    KYFG_BufferGetInfo(streamBufferHandle,
                       KY_STREAM_BUFFER_INFO_SIZE,
                       &bufferSize,
                       NULL,
                       NULL);

    KYFG_BufferGetInfo(streamBufferHandle,
                       KY_STREAM_BUFFER_INFO_USER_PTR,
                       &pUserContext,
                       NULL,
                       NULL);

    KYFG_BufferGetInfo(streamBufferHandle,
                       KY_STREAM_BUFFER_INFO_TIMESTAMP,
                       &timeStamp,
                       NULL,
                       NULL);

    KYFG_BufferGetInfo(streamBufferHandle,
                       KY_STREAM_BUFFER_INFO_INSTANTFPS,
                       &instantFps,
                       NULL,
                       NULL);

    printf(", timeStamp: %" PRIu64 ", instantFps: %f        ", timeStamp, instantFps);

    #endif //#ifndef MINIMAL_CALLBACK
}

#define MAXBOARDS 4
STREAM_HANDLE streamHandle = INVALID_STREAMHANDLE;
CAMHANDLE camHandleArray[MAXBOARDS][KY_MAX_CAMERAS]; // There are maximum KY_MAX_CAMERAS cameras
FGHANDLE m_FgHandles[MAXBOARDS];
int nKayaDevicesCount = 0;

int ConnectToGrabber(unsigned int grabberIndex)
{
    if((m_FgHandles[grabberIndex] = KYFG_Open(grabberIndex)) != -1) // connect to selected device
    {
        printf("Good connection to grabber #%d, handle=%X\n", grabberIndex, m_FgHandles[grabberIndex] );
        return KYTRUE;
    }
    else
    {
        printf("Could not connect to grabber #%d\n", grabberIndex);
        BlockingInput();
        return KYFALSE;
    }
}

void CloseGrabbers()
{
    for(int i = 0; i < nKayaDevicesCount; i++)
    {
        if(INVALID_FGHANDLE != m_FgHandles[i])
        {
            if(FGSTATUS_OK != KYFG_Close(m_FgHandles[i])) // Close the selected device and unregisters all associated routines
            {
                printf("Wasn't able to close grabber #%d\n", i);
            }
            else
            {
                printf("Grabber #%d closed\n", i);
            }
        }
    }
}

void Close(int returnCode)
{
    printf("Input any char to exit\n");
    BlockingInput();
    exit(returnCode);
}

int main()
{
    int grabberIndex = 0, cameraIndex = 0;
    int detectedCameras[MAXBOARDS];
    KYFGLib_InitParameters kyInit;
    char c = 0;
    KY_DEVICE_INFO* grabbersInfoArray = NULL;
    KYFGCAMERA_INFO2* cameraInfoArray = NULL;
    KYBOOL streamRunning = KYFALSE;

    // Comment out the folowing #define to see how acquisition buffers can be allocated by user

    #define FGLIB_ALLOCATED_BUFFERS
    #ifndef FGLIB_ALLOCATED_BUFFERS
    STREAM_BUFFER_HANDLE streamBufferHandle[16] = { 0 };
    size_t frameDataSize, frameDataAligment;
    int i;
    #endif

    // Initialize library

    memset(&kyInit, 0, sizeof(kyInit));
    kyInit.version = 1;

    if(FGSTATUS_OK != KYFGLib_Initialize(&kyInit))
    {
        printf("Library initialization failed\n");
        Close(-1);
    }

    for(int i = 0; i < MAXBOARDS; i++)
    {
        m_FgHandles[i] = INVALID_FGHANDLE;
    }

    // Scan for grabbers

    KY_DeviceScan(&nKayaDevicesCount); // Retrieve the number of virtual and hardware devices connected to PC

    if(!nKayaDevicesCount)
    {
        printf("No PCI devices found\n");
        Close(0);
    }

    grabbersInfoArray = malloc(nKayaDevicesCount * sizeof(KY_DEVICE_INFO));

    for(int i = 0; i < nKayaDevicesCount; i++)
    {
        grabbersInfoArray[i].version = KY_MAX_DEVICE_INFO_VERSION;

        if(FGSTATUS_OK != KY_DeviceInfo(i, &grabbersInfoArray[i]))
        {
            printf("Wasn't able to retrive information from device #%d\n", i);
            continue;
        }
    }

    // Select and open grabber

    KYBOOL grabberReady = KYFALSE;

    while(!grabberReady)
    {
        // Select framegrabber

        printf("Select and open grabber:\n");
        for(int i = 0; i < nKayaDevicesCount; i++)
        {
            printf("[%d] %s on PCI slot {%d:%d:%d}: Protocol 0x%X, Generation %d\n",
                i,
                grabbersInfoArray[i].szDeviceDisplayName,
                grabbersInfoArray[i].nBus,
                grabbersInfoArray[i].nSlot,
                grabbersInfoArray[i].nFunction,
                grabbersInfoArray[i].m_Protocol,
                grabbersInfoArray[i].DeviceGeneration);
        }

        KYBOOL inputValid = KYFALSE;

        while(!inputValid)
        {
            NumberInRangeInput(0, nKayaDevicesCount - 1, &grabberIndex, "Invalid index\n");

            printf("Selected grabber #%d\n", grabberIndex);
            inputValid = KYTRUE;
            break;
        }

        // Connect to framegrabber

        if(ConnectToGrabber(grabberIndex))
        {
            grabberReady = KYTRUE;

            break;
        }
    }

    // Detect and connect camera

    KYBOOL cameraReady = KYFALSE;

    while(!cameraReady)
    {
        KYBOOL cameraScaned = KYFALSE;

        while(!cameraScaned)
        {
            printf("\nPress [d] to detect cameras\n");

            CharInput('d', "Invalid input\n");

            int nDetectedCameras = _countof(camHandleArray[0]);

            if(FGSTATUS_OK != KYFG_UpdateCameraList(m_FgHandles[grabberIndex], camHandleArray[grabberIndex], &nDetectedCameras))
            {
                printf("Camera detect error. Please try again\n");
                continue;
            }

            if(!nDetectedCameras)
            {
                printf("No cameras detected. Please connect at least one camera\n");
                continue; // No cameras were detected
            }

            printf("Number of cameras connected to the PCI device #%d: %d\n", grabberIndex, nDetectedCameras);

            detectedCameras[grabberIndex] = nDetectedCameras;

            if(cameraInfoArray)
            {
                free(cameraInfoArray);
            }

            cameraInfoArray = malloc(nDetectedCameras * sizeof(KYFGCAMERA_INFO2));

            for(int i = 0; i < nDetectedCameras; i++)
            {
                cameraInfoArray[i].version = 1;
                KYFG_CameraInfo2(camHandleArray[grabberIndex][i], &cameraInfoArray[i]);
            }

            cameraScaned = KYTRUE;

            break;
        }

        KYBOOL cameraConnected = KYFALSE;

        while(!cameraConnected)
        {
            printf("\nSelect and connect camera:\n");
            for(cameraIndex = 0; cameraIndex < detectedCameras[grabberIndex]; cameraIndex++)
            {
                printf("[%d] %s: Firmware %s\n",
                    cameraIndex,
                    cameraInfoArray[cameraIndex].deviceModelName,
                    cameraInfoArray[cameraIndex].deviceFirmwareVersion);
            }

            NumberInRangeInput(0, detectedCameras[grabberIndex] - 1, &cameraIndex, "Invalid index\n");

            // Open a connection to chosen camera
            if(FGSTATUS_OK == KYFG_CameraOpen2(camHandleArray[grabberIndex][cameraIndex], 0))
            {
                printf("Camera 0 was connected successfully\n");
                
                KYFG_SetCameraValueInt(camHandleArray[grabberIndex][cameraIndex], "Width", 640); // Set camera width 
                KYFG_SetCameraValueInt(camHandleArray[grabberIndex][cameraIndex], "Height", 480); // Set camera height
                KYFG_SetCameraValueEnum_ByValueName(camHandleArray[grabberIndex][cameraIndex], "PixelFormat", "Mono8"); // Set camera pixel format

                KYFG_SetGrabberValueInt(m_FgHandles[grabberIndex], "CameraSelector", 1 - cameraIndex);
                KYFG_SetGrabberValueInt(camHandleArray[grabberIndex][cameraIndex], "Width", 640);

#ifdef FGLIB_ALLOCATED_BUFFERS
#pragma message("Building with KYFGLib allocated buffers")
                // Let KYFGLib allocate acquisition buffers 
                if (FGSTATUS_OK != KYFG_StreamCreateAndAlloc(camHandleArray[grabberIndex][cameraIndex], &streamHandle, 16, 0))
                {
                    printf("Failed to allocate buffer.\n");
                }

                KYFG_StreamBufferCallbackRegister(streamHandle, Stream_callback_func, NULL);

#else // Advanced example - custom allocation of acquisition buffers:

#pragma message("Building with user allocated buffers")

                // Create stream
                KYFG_StreamCreate(camHandleArray[grabberIndex][cameraIndex], &streamHandle, 0);

                // Retrieve information about required frame buffer size and alignment 
                KYFG_StreamGetInfo(streamHandle,
                    KY_STREAM_INFO_PAYLOAD_SIZE,
                    &frameDataSize,
                    NULL, NULL);
                KYFG_StreamGetInfo(streamHandle,
                    KY_STREAM_INFO_BUF_ALIGNMENT,
                    &frameDataAligment,
                    NULL, NULL);

                // Allocate required amount of frames and announce them to the KYFGLib
                for (i = 0; i < _countof(streamBufferHandle); i++)
                {
                    void * pBuffer = _aligned_malloc(frameDataSize, frameDataAligment);
                    KYFG_BufferAnnounce(streamHandle,
                        pBuffer,
                        frameDataSize,
                        NULL,
                        &streamBufferHandle[i]);
                }

                // Link all frames into a cyclic buffer
                KYFG_StreamLinkFramesContinuously(streamHandle);

#endif // Advanced example - custom allocation of acquisition buffers:

                cameraConnected = KYTRUE;
                cameraReady = KYTRUE;
                break;
            }
            else
            {
                printf("Camera isn't connected\n");
                continue;
            }
        }
    }

    // Start/Stop stream
    
    while(c != 'e')
    {
        printf("\nSelect option:\n");
        printf("[s] %s stream\n", streamRunning ? "Stop" : "Start");
        printf("[e] Exit\n");

        c = BlockingInput();

        if('s' == c)
        {
            streamRunning = 1 - streamRunning;

            if(streamRunning)
            {
                KYFG_CameraStart(camHandleArray[grabberIndex][cameraIndex], streamHandle, 0);
            }
            else
            {
                // Optional: collect some statistic
                int64_t RXFrameCounter = KYFG_GetGrabberValueInt(camHandleArray[grabberIndex][cameraIndex], "RXFrameCounter");
                int64_t DropFrameCounter = KYFG_GetGrabberValueInt(camHandleArray[grabberIndex][cameraIndex], "DropFrameCounter");
                int64_t RXPacketCounter = KYFG_GetGrabberValueInt(camHandleArray[grabberIndex][cameraIndex], "RXPacketCounter");
                int64_t DropPacketCounter = KYFG_GetGrabberValueInt(camHandleArray[grabberIndex][cameraIndex], "DropPacketCounter");

                printf("\nStream statistic:\n");
                printf("RXFrameCounter: %" PRId64 "\n", RXFrameCounter);
                printf("DropFrameCounter: %" PRId64 "\n", DropFrameCounter);
                printf("RXPacketCounter: %" PRId64 "\n", RXPacketCounter);
                printf("DropPacketCounter: %" PRId64 "\n", DropPacketCounter);

                KYFG_CameraStop(camHandleArray[grabberIndex][cameraIndex]);
            }
        }
    }

    // Close grabbers

    CloseGrabbers();

    // Clean-up all open resources

    if(grabbersInfoArray)
    {
        free(grabbersInfoArray); // Release grabbers info
    }

    Close(0);
}



/************************************************************************
*   File: KYFGLib_Example_QueuedBuffers.cpp
*   Sample Frame Grabber API application
*
*   KAYA Instruments Ltd.
*************************************************************************/

#include "stdafx.h"

#include "KYFGLib.h"


#if !defined(_countof)
#define _countof(_Array) (sizeof(_Array) / sizeof(_Array[0]))
#endif

#define KY_MAX_BOARDS 4
FGHANDLE m_FgHandles[KY_MAX_BOARDS];
unsigned int currentGrabberIndex;
int printCxp2Events = 0;
int printHeartbeats = 0;

#ifdef __linux__ // _aligned_malloc() implementation for __linux__
#include <signal.h>
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
#define _aligned_free free
#endif // #ifdef __linux__

#ifndef _MSC_VER
#define scanf_s scanf
#endif

// Helper functions to get user input
char BlockingInput()
{
    char c = -1;
    #ifdef _MSC_VER
    while (scanf_s(" %c", &c, (unsigned int)(sizeof(char))) == -1);
    #else
    while ( (c == -1) || (c == '\n'))
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

//#define FGLIB_ALLOCATED_BUFFERS // Uncomment this #definition to use buffers allocated by KYFGLib
#define MINIMAL_CALLBACK

#define MAXBOARDS 4
CAMHANDLE camHandleArray[KY_MAX_BOARDS][KY_MAX_CAMERAS]; // There are maximum KY_MAX_CAMERAS cameras
STREAM_HANDLE cameraStreamHandle = INVALID_STREAMHANDLE;
FGHANDLE m_FgHandles[MAXBOARDS];
int nKayaDevicesCount = 0;
int64_t dmaImageIdCapable = 0;
int grabberIndex = 0, cameraIndex = 0;

void Stream_callback_func(STREAM_BUFFER_HANDLE streamBufferHandle, void* userContext)
{
    unsigned char* pFrameMemory = 0;
    uint32_t frameId = 0;
#ifndef MINIMAL_CALLBACK
    uint64_t imageId = 0;
    size_t bufferSize = 0;
    void* pUserContext;
    uint64_t timeStamp;
    double instantFps;
#endif
    userContext; // Suppress warning

    if(NULL_STREAM_BUFFER_HANDLE == streamBufferHandle)
    {
        // This callback indicates that acquisition has stopped
        return;
    }

    // As a minimum, application needs to get pointer to current frame memory
    KYFG_BufferGetInfo(streamBufferHandle,
        KY_STREAM_BUFFER_INFO_BASE,
        &pFrameMemory,
        NULL,
        NULL);


    // Additionaly the following information can be obtained:
#ifndef MINIMAL_CALLBACK
    if(1 == dmaImageIdCapable)
    {
        KYFG_BufferGetInfo(streamBufferHandle,
            KY_STREAM_BUFFER_INFO_IMAGEID,
            &imageId,
            NULL,
            NULL);
    }

    KYFG_BufferGetInfo(streamBufferHandle,
        KY_STREAM_BUFFER_INFO_ID,
        &frameId,
        NULL,
        NULL);

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

#endif
    printf(//"\n" // Uncomment to print on new line each time
        "\rGood callback stream's buffer handle:%" PRISTREAM_BUFFER_HANDLE ", ID:%d", streamBufferHandle, frameId);

    // Return stream buffer to input queue
    KYFG_BufferToQueue(streamBufferHandle, KY_ACQ_QUEUE_INPUT);
}

void ProcessHeartbeatEvent(KYDEVICE_EVENT_CXP2_HEARTBEAT* pEventHeartbeat)
{
    if(!printHeartbeats)
    {
        return;
    }
    printf(//"\n" // Uncomment to print on new line each time
        "\rReceived KYDEVICE_EVENT_CXP2_HEARTBEAT: cameraTime=%" PRIu64, pEventHeartbeat->heartBeat.cameraTime);
}

void ProcessCxp2Event(KYDEVICE_EVENT_CXP2_EVENT* pEventCXP2Event)
{
    if (!printCxp2Events)
    {
        return;
    }

    printf("Received KYDEVICE_EVENT_CXP2_EVENT: tag=0x%" PRIu8 "\n", pEventCXP2Event->cxp2Event.tag);
}

void KYDeviceEventCallBackImpl(void* userContext, KYDEVICE_EVENT* pEvent)
{
    userContext; // Suppress warning
    switch(pEvent->eventId)
    {
        // Please note that the following events will be recieved only if camera is working in CXP 2 mode. For details please reffer CXP 2 standards
        case KYDEVICE_EVENT_CXP2_HEARTBEAT_ID:
            ProcessHeartbeatEvent((KYDEVICE_EVENT_CXP2_HEARTBEAT*)pEvent);
            break;

        case KYDEVICE_EVENT_CXP2_EVENT_ID:
            ProcessCxp2Event((KYDEVICE_EVENT_CXP2_EVENT*)pEvent);
            break;
    }
}

int ConnectToGrabber(unsigned int _grabberIndex)
{
    int64_t dmaQueuedBufferCapable;
    int64_t interprocessSharingCapable;

    if((m_FgHandles[_grabberIndex] = KYFG_Open(_grabberIndex)) != -1) // Connect to selected device
    {
        printf("Good connection to grabber #%d, m_FgHandles=%X\n", _grabberIndex, m_FgHandles[_grabberIndex]);
    }
    else
    {
        printf("Could not connect to grabber #%d\n", _grabberIndex);
        BlockingInput();
        return 0;
    }

    dmaQueuedBufferCapable = KYFG_GetGrabberValueInt(m_FgHandles[_grabberIndex], DEVICE_QUEUED_BUFFERS_SUPPORTED);
    interprocessSharingCapable = KYFG_GetGrabberValueInt(m_FgHandles[_grabberIndex], DEVICE_INTERPROCESS_SHARING_SUPPORTED);

    if(1 != dmaQueuedBufferCapable)
    {
        printf("Grabber #%d does not support queued buffers\n", _grabberIndex);
        BlockingInput();
        return 0;
    }

    dmaImageIdCapable = KYFG_GetGrabberValueInt(m_FgHandles[_grabberIndex], DEVICE_IMAGEID_SUPPORTED);

    printf("Grabber #%d, KY_STREAM_BUFFER_INFO_IMAGEID %ssupported\n", _grabberIndex, dmaImageIdCapable ? "" : "not ");

    currentGrabberIndex = _grabberIndex;

    // OPTIONALY register grabber's event callback function
    if(FGSTATUS_OK != KYDeviceEventCallBackRegister(m_FgHandles[_grabberIndex], KYDeviceEventCallBackImpl, 0))
    {
        printf("Warning: KYDeviceEventCallBackRegister() failed\n");
    }

    return 1;
}

int StartCamera(unsigned int _grabberIndex, unsigned int _cameraIndex)
{
    // Put all buffers to input queue
    KYFG_BufferQueueAll(cameraStreamHandle, KY_ACQ_QUEUE_UNQUEUED, KY_ACQ_QUEUE_INPUT);

    // Start acquisition
    KYFG_CameraStart(camHandleArray[_grabberIndex][_cameraIndex], cameraStreamHandle, 0);

    return 0;
}

void CloseGrabbers()
{
    for(int i = 0; i < nKayaDevicesCount; i++)
    {
        if(INVALID_FGHANDLE != m_FgHandles[i])
        {
            if (FGSTATUS_OK != KYFG_Close(m_FgHandles[i])) // Close the selected device and unregisters all associated routines
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

void stopStream()
{
    if (camHandleArray[grabberIndex][cameraIndex] != INVALID_CAMHANDLE)
    {
        if (FGSTATUS_OK == KYFG_CameraStop(camHandleArray[grabberIndex][cameraIndex]))
        {
            printf("\nCamera successfully stoped\n");
        }
    }
    if (cameraStreamHandle != INVALID_STREAMHANDLE)
    {
        if (FGSTATUS_OK == KYFG_StreamDelete(cameraStreamHandle))
        {
            printf("Stream successfully deleted\n");
        }
    }
    
}
#ifdef __linux__
void crash_handler(int signum)
{
    switch (signum)
        /// from https://pubs.opengroup.org/onlinepubs/009695399/basedefs/signal.h.html
    {
        case SIGABRT:
        case SIGFPE:
        case SIGTERM:
        {
            stopStream();
            Close(0);
            break;
        }
    }
}
#endif

int main()
{
    size_t frameDataSize, frameDataAligment;
    STREAM_BUFFER_HANDLE streamBufferHandle[16] = { 0 };
    void *pBuffer[_countof(streamBufferHandle)] = { NULL };
    int detectedCameras[KY_MAX_BOARDS];
    char c = 0;
    KYFGLib_InitParameters kyInit;
    KY_DEVICE_INFO* grabbersInfoArray = NULL;
    KYFGCAMERA_INFO2* cameraInfoArray = NULL;
    KYBOOL streamRunning = KYFALSE;
    // Register Signals
#ifdef __linux__
    signal(SIGABRT, crash_handler);
    signal(SIGFPE, crash_handler);
    signal(SIGTERM, crash_handler);
#endif 
    // Initialize library

    memset(&kyInit, 0, sizeof(kyInit));
    kyInit.version = 2;
    kyInit.concurrency_mode = 0;
    kyInit.logging_mode = 0;
    kyInit.noVideoStreamProcess = KYFALSE;

    if(FGSTATUS_OK != KYFGLib_Initialize(&kyInit))
    {
        printf("Library initialization failed \n ");
        Close(-1);
    }

    for(int i = 0; i < KY_MAX_BOARDS; i++)
    {
        m_FgHandles[i] = INVALID_FGHANDLE;
    }

    // Scan for grabbers

    KY_DeviceScan(&nKayaDevicesCount);    // Retrieve the number of virtual and hardware devices connected to PC

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

            // Open a connection to the chosen camera
            if(FGSTATUS_OK == KYFG_CameraOpen2(camHandleArray[grabberIndex][cameraIndex], NULL))
            {
                printf("Camera #%d was connected successfully\n", cameraIndex);

                // Update camera/grabber buffer dimensions parameters before stream creation
                KYFG_SetCameraValueInt(camHandleArray[grabberIndex][cameraIndex], "Width", 640); // set camera width 
                KYFG_SetCameraValueInt(camHandleArray[grabberIndex][cameraIndex], "Height", 480); // set camera height
                KYFG_SetCameraValueEnum_ByValueName(camHandleArray[grabberIndex][cameraIndex], "PixelFormat", "Mono8"); // set camera pixel format

                // Create stream and assign appropriate runtime acquisition callback function
                KYFG_StreamCreate(camHandleArray[grabberIndex][cameraIndex], &cameraStreamHandle, 0);
                KYFG_StreamBufferCallbackRegister(cameraStreamHandle, Stream_callback_func, NULL);

                // Retrieve information about required frame buffer size and alignment 
                KYFG_StreamGetInfo(cameraStreamHandle,
                    KY_STREAM_INFO_PAYLOAD_SIZE,
                    &frameDataSize,
                    NULL, NULL);

                KYFG_StreamGetInfo(cameraStreamHandle,
                    KY_STREAM_INFO_BUF_ALIGNMENT,
                    &frameDataAligment,
                    NULL, NULL);

                // Allocate memory for desired number of frame buffers
                for(int iFrame = 0; iFrame < _countof(streamBufferHandle); iFrame++)
                {
#ifdef FGLIB_ALLOCATED_BUFFERS
#pragma message("Building with KYFGLib allocated buffers")
                    KYFG_BufferAllocAndAnnounce(cameraStreamHandle,
                        frameDataSize,
                        NULL,
                        &streamBufferHandle[iFrame]);
#else
#pragma message("Building with user allocated buffers")
                    pBuffer[iFrame] = _aligned_malloc(frameDataSize, frameDataAligment);
                    KYFG_BufferAnnounce(cameraStreamHandle,
                        pBuffer[iFrame],
                        frameDataSize,
                        NULL,
                        &streamBufferHandle[iFrame]);
#endif 

                }

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
        printf("[v] CXP events %s\n", printCxp2Events ? "off" : "on");
        printf("[h] Heartbeats %s\n", printHeartbeats ? "off" : "on");
#ifdef __linux__
        printf("[f] Generate SIGFPE signal (Devision by zero)\n");
        printf("[a] Generate SIGABRT signal (call abort() func)\n");
#endif
        printf("[e] Exit\n");

        c = BlockingInput();

        if('s' == c)
        {
            streamRunning =  1 - streamRunning;

            if(streamRunning)
            {
                StartCamera(grabberIndex, cameraIndex);
            }
            else
            {
                // Optional: collect some statistic before stopping
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

        if('h' == c)
        {
            printHeartbeats = 1 - printHeartbeats; // Toggle 'printHeartbeats' between 0 and 1
        }

        if('v' == c)
        {
            printCxp2Events = 1 - printCxp2Events; // Toggle 'printCxp2Events' between 0 and 1
        }
#ifdef __linux__
        if ('a' == c)
        {
            abort();
        }
        if ('f' == c)
        {
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wdiv-by-zero"
            int fail = 5 / 0;
#pragma GCC diagnostic pop
        }
#endif
    }

    // Close grabbers

    CloseGrabbers();

    // Clean-up all open resources

    if(grabbersInfoArray)
    {
        free(grabbersInfoArray); // Release grabbers info
    }

    if(cameraInfoArray)
    {
        free(cameraInfoArray); // Release cameras info
    }

    // Release pBuffer

    for(int iFrame = 0; iFrame < _countof(streamBufferHandle); iFrame++)
    {
        if(pBuffer[iFrame])
        {
            _aligned_free(pBuffer[iFrame]);
            pBuffer[iFrame] = NULL;
        }
    }

    Close(0);
}

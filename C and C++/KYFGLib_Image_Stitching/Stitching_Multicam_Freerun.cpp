/************************************************************************ 
 * @file    Stitching_Multicam_Freerun.cpp
 * @brief   Example for image stitching from multiple cameras.
 * @details KYFG_BufferAnnounceChunks API function is used for the construction
 *          of a composite image from chunks assigned to multiple cameras. 
            The cameras are configured to run in freerun mode with the same frame rate.
 * @pre     To compile the example, OpenCV SDK should be configured in the system.
 *
 * @author  KAYA Instruments Ltd.
 *************************************************************************/

#include "stdafx.h"
#include "KYFGLib.h"
#include "opencv2/opencv.hpp"
#include <thread>
#include <mutex>
#include <chrono>
#include <condition_variable>

#if !defined(_countof)
#define _countof(_Array) (sizeof(_Array) / sizeof(_Array[0]))
#endif

#ifdef __GNUC__ // _aligned_malloc() implementation for gcc
void* _aligned_malloc(size_t size, size_t alignment)
{
    size_t pageAlign = size % 4096;
    if(pageAlign)
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

void _aligned_free(void* pMemory)
{
    free(pMemory);
}

#endif // #ifdef __GNUC__

// Helper function to get single printable char as user input
char BlockingInput()
{
    char c;
    while (scanf(" %c", &c) == -1);
    return c;
}

// The following settings will be applied for each camera
#define IMAGE_WIDTH 2048
#define IMAGE_HEIGHT 2048
#define FRAME_RATE 30.0
#define BUFFER_COUNT 8

typedef struct
{
    FGHANDLE grabberHandle = INVALID_FGHANDLE;
    CAMHANDLE camHandle = INVALID_CAMHANDLE;
    STREAM_HANDLE streamHandle = INVALID_STREAMHANDLE;
    STREAM_BUFFER_HANDLE streamBufferHandleArr[BUFFER_COUNT] = { 0 };
    bool bFrameCaptured = false;
}CameraStreamData_t;

std::vector<CameraStreamData_t> cameraStreamDataArray;
std::thread imageShowThread;
std::mutex imageStreamMutex;
std::mutex imageShowMutex;
std::condition_variable imageShowConditionVariable;
uint8_t* g_pImageDisplay = NULL; // Display image memory

// Stitched image data
uint8_t* g_pImageMemory[BUFFER_COUNT] = {NULL};
size_t g_totalImageHeight = 0; // Value will be updated after N cameras are detected
size_t g_totalImageWidth = 0; // Value will be updated after N cameras are detected
size_t g_displayImageHeight = 0; // Display image height
size_t g_displayImageWidth = 0; // Display image width

static int MINIMUM_FRAME_PERIOD = 100; //ms
static auto last_frame_time = std::chrono::system_clock::now();

double instantFps;
int nKayaDevicesCount = 0;

void ImageShowThreadFunc()
{
    const char* sStreamStitchingWindowName = "StreamStitchingWindow";
    cv::Mat imgMat(cv::Size((int)g_totalImageWidth, (int)g_totalImageHeight), CV_8U, g_pImageDisplay);

    while(g_pImageDisplay)
    {
        std::unique_lock<std::mutex> lock(imageShowMutex);
        imageShowConditionVariable.wait(lock);

        if(!g_pImageDisplay)
        {
            #if CV_VERSION_MAJOR >= 4
            if(cv::getWindowProperty(sStreamStitchingWindowName, cv::WND_PROP_VISIBLE) > 0)
            #endif
            {
                cv::destroyWindow(sStreamStitchingWindowName);
            }
            printf("Terminate ImageShowThreadFunc\n\r");
            return;
        }

        cv::Mat displayMat;
        cv::resize(imgMat, displayMat, cv::Size((int)g_displayImageWidth, (int)g_displayImageHeight));

        cv::imshow(sStreamStitchingWindowName, displayMat);
        cv::waitKey(1);
       
    }
}

void Stream_callback_func(STREAM_BUFFER_HANDLE streamBufferHandle, void* userContext)
{
    if(!streamBufferHandle)
    {
        // This callback indicates that acquisition has stopped
        return;
    }

    CameraStreamData_t* pCameraStreamData = (CameraStreamData_t*)userContext;

    int bufferIndex = 0;
    for(int iBuffer = 0; iBuffer < _countof(pCameraStreamData->streamBufferHandleArr); iBuffer++)
    {
        if(streamBufferHandle == pCameraStreamData->streamBufferHandleArr[iBuffer])
        {
            bufferIndex = iBuffer;
        }
    }

    printf(//"\n" // Uncomment to print on new line each time
        "\rGood callback stream's buffer handle:%" PRISTREAM_BUFFER_HANDLE ", ID:%02" PRIu32, streamBufferHandle, bufferIndex);

    pCameraStreamData->bFrameCaptured = true;

    std::lock_guard<std::mutex> lock(imageStreamMutex);

    if(true == pCameraStreamData->bFrameCaptured)
    {
        const int64_t frameCapturedCheckTimeout = 1000; // 1000 msec
        bool bFrameCapturedFromAllCameras = true;
        auto start = std::chrono::steady_clock::now();
        int64_t timeElapsedMs = 0;
        do {
            bFrameCapturedFromAllCameras = true;

            // Check that all streams have received a frame
            for (CameraStreamData_t& cameraStreamData : cameraStreamDataArray)
            {
                if(false == cameraStreamData.bFrameCaptured)
                {
                    bFrameCapturedFromAllCameras = false;
                    break;
                }
            }
            auto end = std::chrono::steady_clock::now();
            timeElapsedMs = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();
        }while((!bFrameCapturedFromAllCameras) && (timeElapsedMs < frameCapturedCheckTimeout));

        if(timeElapsedMs < frameCapturedCheckTimeout)
        {
            // Stitched image data
            auto cur_frame_time = std::chrono::system_clock::now();
            if (std::chrono::duration_cast<std::chrono::milliseconds>(cur_frame_time - last_frame_time).count() >= MINIMUM_FRAME_PERIOD)
            {
                memcpy(g_pImageDisplay, g_pImageMemory[bufferIndex], g_totalImageWidth * g_totalImageHeight);
                imageShowConditionVariable.notify_one(); // Wake ImageShowThreadFunc()
                last_frame_time = cur_frame_time;
            }
        }
        else
        {
            printf("Timeout error in frame %d capture\n\r", bufferIndex);
        }

        // Clear indication that frame was captured for all streams
        for(CameraStreamData_t& cameraStreamData : cameraStreamDataArray)
        {
            cameraStreamData.bFrameCaptured = false;
        }
    }
        

    KYFG_BufferToQueue(streamBufferHandle, KY_ACQ_QUEUE_INPUT);
}

FGHANDLE ConnectToGrabber(int grabberIndex)
{
    FGHANDLE grabberHandle = INVALID_FGHANDLE;
    KY_DEVICE_INFO deviceInfo;
    memset(&deviceInfo, 0, sizeof(KY_DEVICE_INFO));
    deviceInfo.version = KY_MAX_DEVICE_INFO_VERSION;
    if(FGSTATUS_OK != KY_DeviceInfo(grabberIndex, &deviceInfo))
    {
        printf("wasn't able to retrive information from device #%d\n", grabberIndex);
        return INVALID_FGHANDLE;
    }

    if((grabberHandle = KYFG_Open(grabberIndex)) != INVALID_FGHANDLE)     // connect to selected device
    {
        printf("Good connection to grabber #%d, handle=%X\n", grabberIndex, grabberHandle);
    }
    else
    {
        printf("Could not connect to grabber #%d\n", grabberIndex);
        return INVALID_FGHANDLE;
    }

    int64_t imageStitchingCapable = KYFG_GetGrabberValueInt(grabberHandle, DEVICE_IMAGE_STITCHING_SUPPORTED);
    if(1 != imageStitchingCapable)
    {
        printf("Grabber #%d does not support image stitching\n", grabberIndex);
        KYFG_Close(grabberHandle); // close the grabber because it doesn't support image stitching
        return INVALID_FGHANDLE;
    }

    printf("[%d] %s on PCI slot {%d:%d:%d}: Protocol 0x%X, Generation %d\n", grabberIndex,
        deviceInfo.szDeviceDisplayName,
        deviceInfo.nBus, deviceInfo.nSlot, deviceInfo.nFunction,
        deviceInfo.m_Protocol, deviceInfo.DeviceGeneration);

    return grabberHandle;
}

int StartCamera(CameraStreamData_t& cameraStreamData)
{
    // Put all buffers to input queue
    KYFG_BufferQueueAll(cameraStreamData.streamHandle, KY_ACQ_QUEUE_UNQUEUED, KY_ACQ_QUEUE_INPUT);

    // Start acquisition
    KYFG_CameraStart(cameraStreamData.camHandle, cameraStreamData.streamHandle, 0);

    return 0;
}

int StopCamera(CameraStreamData_t& cameraStreamData)
{
    KYFG_CameraStop(cameraStreamData.camHandle);
    return 0;
}

int ImageStitchingUpdateGlobalBuffersInfo()
{
    // Update the memory of the stitched buffers
    if((cameraStreamDataArray.size() > 2) && (0 == cameraStreamDataArray.size() % 2)) // In case of even number of cameras and more than 2
    {
        // ----------------------
        // | cam0 | cam1 | cam2 | ...
        // | cam3 | cam4 | cam5 |
        // ----------------------

        g_totalImageWidth = cameraStreamDataArray.size() / 2 * IMAGE_WIDTH;
        g_totalImageHeight = IMAGE_HEIGHT * 2;

        g_displayImageWidth = g_totalImageWidth * 1080 / g_totalImageHeight;
        g_displayImageHeight = 1080;
    }
    else // In case of odd number of camera or no more than 2 cameras stitch them horizontally
    {
        // ------------------------------------
        // | cam0 | cam1 | cam2 | cam3 | cam4 | ...
        // ------------------------------------

        g_totalImageWidth = cameraStreamDataArray.size() * IMAGE_WIDTH;
        g_totalImageHeight = IMAGE_HEIGHT;

        g_displayImageWidth = 1920;
        g_displayImageHeight = g_totalImageHeight * 1920 / g_totalImageWidth;
    }

    for(size_t iImageBuffer = 0; iImageBuffer < BUFFER_COUNT; iImageBuffer++)
    {
        g_pImageMemory[iImageBuffer] = (uint8_t*)_aligned_malloc(g_totalImageWidth*g_totalImageHeight, 4096);
    }

    g_pImageDisplay = (uint8_t*)_aligned_malloc(g_totalImageWidth*g_totalImageHeight, 4096);

    imageShowThread = std::thread(ImageShowThreadFunc); // Create the image thread

    return 0;
}

int ImageStitchingConstructBufferChunks(size_t cameraIndex, size_t totalCameras, CameraStreamData_t& cameraStreamData)
{
    size_t horizontalOffset = 0;
    size_t verticalOffset = 0;

    if((totalCameras > 2) && (0 == totalCameras % 2)) // In case of even number of cameras and more than 2
    {
        // ----------------------
        // | cam0 | cam1 | cam2 | ...
        // | cam3 | cam4 | cam5 |
        // ----------------------

        horizontalOffset = (cameraIndex % (totalCameras / 2)) * IMAGE_WIDTH;
        verticalOffset = cameraIndex / (totalCameras / 2) * IMAGE_HEIGHT;
    }
    else // In case of odd number of camera or no more than 2 cameras stitch them horizontally
    {
        // ------------------------------------
        // | cam0 | cam1 | cam2 | cam3 | cam4 | ...
        // ------------------------------------

        horizontalOffset = cameraIndex * IMAGE_WIDTH;
        verticalOffset = 0; // 1 line only
    }


    auto timeStart = std::chrono::steady_clock::now();

    // Allocate memory for desired number of frame buffers
    for(size_t iImageBuffer = 0; iImageBuffer < BUFFER_COUNT; iImageBuffer++)
    {
        uint8_t* pBuffer = g_pImageMemory[iImageBuffer] + (verticalOffset * g_totalImageWidth); // Memery to start of left image 

        std::vector<BUFFER_DATA_CHUNK> dataChunkArr;
        for(size_t iRow = 0; iRow < IMAGE_HEIGHT; iRow++)
        {
            BUFFER_DATA_CHUNK dataChunk = { pBuffer + horizontalOffset, IMAGE_WIDTH };
            dataChunkArr.push_back(dataChunk);

            pBuffer += g_totalImageWidth;
        }

        FGSTATUS status = KYFG_BufferAnnounceChunks(cameraStreamData.streamHandle, // STREAM_HANDLE streamHandle
            dataChunkArr.data(),// BUFFER_DATA_CHUNK* pDataChunkArr, 
            dataChunkArr.size(),// size_t nChunks,
            NULL,// void * pPrivate
            &cameraStreamData.streamBufferHandleArr[iImageBuffer]);

        if(FGSTATUS_OK != status)
        {
            printf("KYFG_BufferAnnounceChunks for stream 0x%" PRISTREAM_HANDLE " failed with error 0%" PRIX32 "\n\r", cameraStreamData.streamHandle, status);
        }
    }

    int64_t timePassed = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - timeStart).count();
    printf("ImageStitchingConstructBufferChunks for camera 0x% " PRICAMHANDLE " taken %lld msec\n\r", cameraStreamData.camHandle, timePassed);

    return 0;
}

void Close(int returnCode)
{
    printf("Input any char to exit\n");
    BlockingInput();
    exit(returnCode);
}

int main()
{
    char c = 0;
    KYFGLib_InitParameters kyInit;
    KYBOOL streamRunning = KYFALSE;

    kyInit.version = 2;
    kyInit.concurrency_mode = 0;
    kyInit.logging_mode = 0;
    kyInit.noVideoStreamProcess = KYFALSE;

    // Initialize library

    if(FGSTATUS_OK != KYFGLib_Initialize(&kyInit))
    {
        printf("Library initialization failed \n ");
        return 1;
    }

    FGSTATUS status = FGSTATUS_OK;

    // Scan for grabbers

    KY_DeviceScan(&nKayaDevicesCount); // First scan for device to retrieve the number of virtual and hardware devices connected to PC
    
    if(!nKayaDevicesCount)
    {
        printf("No PCI devices found\n");
        Close(0);
    }

    printf("Number of scan results: %d\n", nKayaDevicesCount);

    // Find all connected grabbers which support image stitching
    for(int i = 0; i < nKayaDevicesCount; i++)
    {
        FGHANDLE grabberHandle = ConnectToGrabber(i);
        if(INVALID_FGHANDLE != grabberHandle)
        {
            CAMHANDLE camHandleArray[KY_MAX_CAMERAS] = { 0 };

            // Scan for connected cameras
            int detectionCount = _countof(camHandleArray);
            
            status = KYFG_UpdateCameraList(grabberHandle, camHandleArray, &detectionCount);
            if((FGSTATUS_OK != status) || (0 == detectionCount))
            {
                KYFG_Close(grabberHandle); // Close grabber and continue because no cameras were detected
                continue;
            }

            // Open and configure all found cameras
            for(int cameraIndex = 0; cameraIndex < detectionCount; cameraIndex++)
            {
                CameraStreamData_t cameraStreamData;
                cameraStreamData.grabberHandle = grabberHandle;
                cameraStreamData.camHandle = camHandleArray[cameraIndex];

                // Open a connection to chosen camera
                if(FGSTATUS_OK == KYFG_CameraOpen2(cameraStreamData.camHandle, NULL))
                {
                    printf("Camera %d on grabber %d was connected successfully\n", cameraIndex, i);
                }
                else
                {
                    printf("Camera isn't connected\n");
                    continue;
                }

                KYFG_SetCameraValueInt(cameraStreamData.camHandle, "Width", IMAGE_WIDTH); // set camera width 
                KYFG_SetCameraValueInt(cameraStreamData.camHandle, "Height", IMAGE_HEIGHT); // set camera height
                
                int64_t WidthMax = 0, WidthMin = 0;
                KYFG_GetCameraValueIntMaxMin(cameraStreamData.camHandle, "Width", &WidthMax, &WidthMin);
                int64_t HeightMax = 0, HeightMin = 0;
                KYFG_GetCameraValueIntMaxMin(cameraStreamData.camHandle, "Height", &HeightMax, &HeightMin);

                KYFG_SetCameraValueInt(cameraStreamData.camHandle, "OffsetX", (WidthMax - IMAGE_WIDTH) / 2);
                KYFG_SetCameraValueInt(cameraStreamData.camHandle, "OffsetY", (HeightMax - IMAGE_HEIGHT) / 2);

                printf("Configure camera 0x%" PRICAMHANDLE " ROI: %dx%d (max: %dx%d), offsetX: %d, offsetY: %d\n\r", 
                                     cameraStreamData.camHandle, (int)IMAGE_WIDTH, (int)IMAGE_HEIGHT, (int)WidthMax, (int)HeightMax, (int)(WidthMax - IMAGE_WIDTH) / 2, (int)(HeightMax - IMAGE_HEIGHT) / 2);

                if(FGSTATUS_OK != KYFG_SetCameraValueEnum_ByValueName(cameraStreamData.camHandle, "PixelFormat", "Mono8")) // Set camera pixel format for monochrome
                {
                    KYFG_SetCameraValueEnum_ByValueName(cameraStreamData.camHandle, "PixelFormat", "BayerRG8"); // Set camera pixel format for color (Bayer) camera
                }

                KYFG_SetCameraValueFloat(cameraStreamData.camHandle, "AcquisitionFrameRate", 30.0); // Set camera acquisition frame rate

                KYFG_SetGrabberValueInt(cameraStreamData.grabberHandle, "CameraSelector", cameraIndex);
                KYFG_SetGrabberValueEnum_ByValueName(cameraStreamData.grabberHandle, "TransferControlMode", "UserControlled");

                cameraStreamDataArray.push_back(cameraStreamData);
            }
        }
    }

    if(0 != cameraStreamDataArray.size())
    {
        printf("%d cameras were found for image stitching\n\r", int(cameraStreamDataArray.size()));

        ImageStitchingUpdateGlobalBuffersInfo();

        for(size_t cameraIndex = 0; cameraIndex < cameraStreamDataArray.size(); cameraIndex++)
        {
            CameraStreamData_t& cameraStreamData = cameraStreamDataArray[cameraIndex];

            // Create stream and assign appropriate runtime acquisition callback function
            KYFG_StreamCreate(cameraStreamData.camHandle, &cameraStreamData.streamHandle, 0);
            KYFG_StreamBufferCallbackRegister(cameraStreamData.streamHandle, Stream_callback_func, &cameraStreamData);

            ImageStitchingConstructBufferChunks(cameraIndex, cameraStreamDataArray.size(), cameraStreamData);
        }
    }
    else
    {
        printf("No cameras detected\n");
        Close(0);
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
                for(CameraStreamData_t& cameraStreamData : cameraStreamDataArray)
                {
                    StartCamera(cameraStreamData);
                }

                for(CameraStreamData_t& cameraStreamData : cameraStreamDataArray)
                {
                    KYFG_CameraExecuteCommand(cameraStreamData.camHandle, "AcquisitionStart");
                }
            }
            else
            {
                for(CameraStreamData_t& cameraStreamData : cameraStreamDataArray)
                {
                    KYFG_CameraExecuteCommand(cameraStreamData.camHandle, "AcquisitionStop");
                }

                for(size_t cameraIndex = 0; cameraIndex < cameraStreamDataArray.size(); cameraIndex++)
                {
                    CameraStreamData_t& cameraStreamData = cameraStreamDataArray[cameraIndex];
                    StopCamera(cameraStreamData);

                    // Optional: collect some statistic

                    KYFG_SetGrabberValueInt(cameraStreamData.grabberHandle, "CameraSelector", cameraIndex);
                    int64_t RXFrameCounter = KYFG_GetGrabberValueInt(cameraStreamData.grabberHandle, "RXFrameCounter");
                    int64_t DropFrameCounter = KYFG_GetGrabberValueInt(cameraStreamData.grabberHandle, "DropFrameCounter");
                    int64_t RXPacketCounter = KYFG_GetGrabberValueInt(cameraStreamData.grabberHandle, "RXPacketCounter");
                    int64_t DropPacketCounter = KYFG_GetGrabberValueInt(cameraStreamData.grabberHandle, "DropPacketCounter");

                    printf("\nCamera %u statistic:\n", (uint32_t)cameraIndex);
                    printf("RXFrameCounter: %" PRId64 "\n", RXFrameCounter);
                    printf("DropFrameCounter: %" PRId64 "\n", DropFrameCounter);
                    printf("RXPacketCounter: %" PRId64 "\n", RXPacketCounter);
                    printf("DropPacketCounter: %" PRId64 "\n", DropPacketCounter);
                }
            }
        }
    }

    // Clean-up all open resources
    
    // Stop all streams
    for(CameraStreamData_t& cameraStreamData : cameraStreamDataArray)
    {
        KYFG_CameraExecuteCommand(cameraStreamData.camHandle, "AcquisitionStop");
        KYFG_CameraStop(cameraStreamData.camHandle);
    }

    // Close all opened cameras
    for(CameraStreamData_t& cameraStreamData : cameraStreamDataArray)
    {
        KYFG_StreamDelete(cameraStreamData.streamHandle);
        KYFG_CameraClose(cameraStreamData.camHandle);
    }

    // Close all opened grabbers
    for(CameraStreamData_t& cameraStreamData : cameraStreamDataArray)
    {
        KYFG_Close(cameraStreamData.grabberHandle);
    }

    // Delete memory of all buffers for stitching
    for(size_t iImageBuffer = 0; iImageBuffer < BUFFER_COUNT; iImageBuffer++)
    {
        if(g_pImageMemory[iImageBuffer])
        {
            _aligned_free(g_pImageMemory[iImageBuffer]);
            g_pImageMemory[iImageBuffer] = NULL;
        }
    }

    // Delete the g_pImageDisplay
    if(g_pImageDisplay)
    {
        std::unique_lock<std::mutex> lock(imageShowMutex);
        _aligned_free(g_pImageDisplay);
        g_pImageDisplay = NULL;
    }

    // Terminate its thread ImageShowThreadFunc
    if(imageShowThread.joinable())
    {
        imageShowConditionVariable.notify_one(); // Wake ImageShowThreadFunc() so it will be terminated
        imageShowThread.join();
    }

    Close(0);
}

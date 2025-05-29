// GenTL_Example.cpp : Defines the entry point for the console application.
//

#include "stdafx.h"

#define CAMERA_XML_ACQUISITION_START_REG        0x1FEFDBB4 // User must set this value according to his camera XML reg.
                                                           // Default value is for Chameleon camera simulator
#define CAMERA_XML_ACQUISITION_START_VALUE      0x01000000

#define CAMERA_XML_ACQUISITION_STOP_REG         0x1FEFDBB0
#define CAMERA_XML_ACQUISITION_STOP_VALUE       0

#define BUFFER_AMOUNT 16

#define STREAM_CALLBACK_COUNT 0 // 0 - infinate
// #define BLOCK_STREAM


#ifdef _WIN32
    #include "windows.h"
    #include <conio.h>
#else
    #define MAX_PATH 256
    #include <stdio.h>
    #include <stdlib.h>
    #include <string.h>
    #include <time.h>
    #include <string.h>
    #include <iostream>
    #include <iomanip>
    #include <termios.h>
    #include <unistd.h>
    #include <sys/types.h>
    #include <sys/time.h>
    #include <thread>
    #include <unistd.h>
    #define Sleep(ms) usleep(ms * 1000)

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
#endif // #ifdef __GNUC__

#ifdef __linux__
    #define _aligned_free free
    #define sscanf_s sscanf
#endif


int _kbhit (void)
{
    struct timeval tv;
    fd_set rdfs;

    tv.tv_sec = 0;
    tv.tv_usec = 0;

    FD_ZERO(&rdfs);
    FD_SET(STDIN_FILENO, &rdfs);

    select(STDIN_FILENO + 1, &rdfs, NULL, NULL, &tv);
    return FD_ISSET(STDIN_FILENO, &rdfs);

}
#endif


#include "GenTL_v1_5.h"
#include "hwcti.h"
#include "ky_os.h"

ky_lib hcti = NULL;
tl_calls tl;

using namespace GenTL;

#define MAX_INTERFACES 8

struct EventDataStruct
{
    DS_HANDLE m_hStream;
    EVENT_HANDLE m_Hevent;
};

TL_HANDLE hTL = nullptr;
uint32_t interfaceIndex = 0;

struct InterfaceInfo
{
    // Inderface device
    IF_HANDLE hIface = GENTL_INVALID_HANDLE;
    DEV_HANDLE hDev = GENTL_INVALID_HANDLE;
    // Camera port
    PORT_HANDLE hDevice = GENTL_INVALID_HANDLE;
    // Stream
    DS_HANDLE hStream = GENTL_INVALID_HANDLE;
    // Event
    EVENT_HANDLE hEvent = GENTL_INVALID_HANDLE; // new buffer event
    std::thread eventThread;
    EventDataStruct eventDataStruct;
    // Buffers
    BUFFER_HANDLE buffHandleArr[BUFFER_AMOUNT] = { GENTL_INVALID_HANDLE };
    unsigned char* buffArrPtr[BUFFER_AMOUNT] = { 0 };
};

InterfaceInfo g_intefaceInfo;


void PrintHelp(void)
{
    printf("\n\r=============================================\n\r"
            "? - help\n\r"
           "[0-7]-select and open interface\n\r"
           "l - close interface\n\r"
#ifndef BLOCK_STREAM
           "s - start acquisition\n\r"
           "t - stop acquisition\n\r"
           //"k - test event kill\n\r"
#endif
           "r <address> - read camera register\n\r"
           "w <address> <value> - write camera register\n\r"
           "x - extract camera xml file\n\r"
           "g - extract grabber xml file\n\r"

           "e - exit\n\r"
           "=============================================\n\r"
    );

}

void PrintDevices(TL_HANDLE hTL)
{
    uint32_t NumInterfaces = 0;
    uint32_t intface = 0;
    char IfaceID[MAX_PATH] = { 0 };
    size_t bufferSize = MAX_PATH;
    INFO_DATATYPE piType;
    char buffer[MAX_PATH] = { 0 };
    bool8_t changed;

    tl.TLUpdateInterfaceList(hTL, &changed, 0);
    tl.TLGetNumInterfaces(hTL, &NumInterfaces);
    printf("\n\rNumber of devices found : %d\n\r", NumInterfaces);

    while (NumInterfaces > intface)
    {
        bufferSize = sizeof(IfaceID);
        tl.TLGetInterfaceID(hTL, intface, IfaceID, &bufferSize);
        //printf("IfaceID : %lls\n\r", IfaceID);
        bufferSize = MAX_PATH;

        // print available devices
        bufferSize = sizeof(buffer);
        tl.TLGetInterfaceInfo(hTL, IfaceID, INTERFACE_INFO_DISPLAYNAME, &piType, buffer, &bufferSize);
        printf("Interface %d: %s\n\r", intface, buffer);

        intface++;
    }
}

bool InitLib( void )
{
#ifdef _WIN32
    static const char* szKayaLibFolderEnv = "KAYA_VISION_POINT_BIN_PATH";
    static const char  chPatSep = '\\';
    static const std::string sKayaLibCtiFile = "KYFGLibGenTL_vc141.cti";
#elif defined(__linux__)
    static const char* szKayaLibFolderEnv = "KAYA_VISION_POINT_LIB_PATH";
    static const char  chPatSep = '/';
    static const std::string sKayaLibCtiFile = "libKYFGLibGenTL.cti";
#endif


    
#ifdef _WIN32
    char* kayaLibEnv = NULL;
    size_t requiredSize;
    errno_t errno_env = _dupenv_s(&kayaLibEnv, &requiredSize, szKayaLibFolderEnv);
#else
    char* kayaLibEnv = getenv(szKayaLibFolderEnv);
#endif
    std::string sKayaLibEnv(kayaLibEnv);
    std::string cti = sKayaLibEnv + chPatSep + sKayaLibCtiFile;

    ky_load_lib(cti.c_str(), hcti);
    if (!hcti)
    {
        printf("The cti file %s failed to load\n\r", cti.c_str());
        getchar();
        return false;
    }

    LOAD_SYMBOLS(tl, hcti);

    // Initiate GenTL library
    tl.GCInitLib();

    return true;
}


//3.8.3 OpenTL
//Retrieve TL Handle
TL_HANDLE OpenTL( void )
{
    tl.TLOpen( &hTL );
    return hTL;
}

//3.8.4 OpenInterface
//Retrieve first Interface Handle
IF_HANDLE OpenInterface(TL_HANDLE hTL )
{
    bool8_t changed;
    uint32_t NumInterfaces = 0;
    char IfaceID[MAX_PATH];
    size_t bufferSize = MAX_PATH;
    IF_HANDLE hNewIface;
    INFO_DATATYPE piType;
    char buffer[MAX_PATH];

    bufferSize = sizeof(buffer);
    tl.TLGetInfo(hTL,TL_INFO_PATHNAME, &piType, buffer, &bufferSize);
//    printf("dll path: %s\n", buffer);

    tl.TLUpdateInterfaceList( hTL , &changed, 0);
    tl.TLGetNumInterfaces( hTL, &NumInterfaces );

    if ( NumInterfaces > interfaceIndex)
    {
        // Get inteface id string
        bufferSize = sizeof(IfaceID);
        tl.TLGetInterfaceID( hTL, interfaceIndex, IfaceID, &bufferSize );
        // Open interface with index 0
        tl.TLOpenInterface( hTL, IfaceID, &hNewIface );
        /*bufferSize = MAX_PATH;
        tl.GCGetPortInfo(hNewIface,PORT_INFO_MODULE, &piType, buffer, &bufferSize);
        printf("module name: %s\n", buffer);*/

        return hNewIface;
    }
    else
    {
        return GENTL_INVALID_HANDLE;
    }
}

//3.8.5 OpenFirstDevice
//Retrieve first Device Handle
PORT_HANDLE OpenFirstDevice( IF_HANDLE hIF )
{
    bool8_t changed;
    uint32_t NumDevices = 0;
    char DeviceID[MAX_PATH];
    size_t bufferSize = MAX_PATH;
    DEV_HANDLE hNewDevice;
    //PORT_HANDLE phRemoteDevice;

    tl.IFUpdateDeviceList( hIF , &changed, 0 );
    tl.IFGetNumDevices( hIF, &NumDevices );

    if ( NumDevices > 0 )
    {
        // First query the buffer size
        bufferSize = sizeof(DeviceID);
        tl.IFGetDeviceID( hIF, 0, DeviceID, &bufferSize );
        int32_t result = 0;
        INFO_DATATYPE piType;
        size_t pSize = sizeof(result);
        tl.IFGetDeviceInfo( hIF, DeviceID, DEVICE_INFO_ACCESS_STATUS, &piType, &result , &pSize);
        // Open interface with index 0
        tl.IFOpenDevice( hIF, DeviceID, DEVICE_ACCESS_CONTROL , &hNewDevice );
        
        return hNewDevice;
    }
    else
    {
        return GENTL_INVALID_HANDLE;
    }
}

//3.8.6 OpenFirstDataStream
//Retrieve first data Stream
DS_HANDLE OpenFirstDataStream( DEV_HANDLE hDev )
{
    uint32_t NumStreams = 0;
    char StreamID[20];
    size_t buffersize = 20;
    DS_HANDLE hNewStream;
    GC_ERROR errorResult;

    // Retrieve the number of Data Stream
    tl.DevGetNumDataStreams( hDev, &NumStreams );
    if ( NumStreams > 0 )
    {
        // Get ID of first stream using
        errorResult = tl.DevGetDataStreamID( hDev, 0, StreamID, &buffersize );
        // Instantiate Data Stream
        errorResult = tl.DevOpenDataStream( hDev, StreamID, &hNewStream );
        return hNewStream;
    }
    else
    {
        return GENTL_INVALID_HANDLE;
    }
}

void OpenDataBuffer(InterfaceInfo* pInterfaceInfo)
{
    size_t dataStreamPayloadSize = 0;
    size_t iSize = sizeof(dataStreamPayloadSize);
    INFO_DATATYPE iType;
    tl.DSGetInfo(pInterfaceInfo->hStream, STREAM_INFO_PAYLOAD_SIZE, &iType, &dataStreamPayloadSize, &iSize );

    for(size_t i = 0 ; i < BUFFER_AMOUNT; ++i)
    {
        pInterfaceInfo->buffArrPtr[i] = (unsigned char*)_aligned_malloc(dataStreamPayloadSize, 4096);
        tl.DSAnnounceBuffer(pInterfaceInfo->hStream, pInterfaceInfo->buffArrPtr[i], dataStreamPayloadSize, nullptr, &pInterfaceInfo->buffHandleArr[i]);
    }
}


void CloseDataBuffer(InterfaceInfo* pInterfaceInfo)
{
    if (!pInterfaceInfo->hStream)
    {
        return;
    }
    
    for (size_t i = 0; i < BUFFER_AMOUNT; ++i)
    {
        if (pInterfaceInfo->buffArrPtr[i])
        {
            _aligned_free(pInterfaceInfo->buffArrPtr[i]);
            pInterfaceInfo->buffArrPtr[i] = nullptr;
            pInterfaceInfo->buffHandleArr[i] = GENTL_INVALID_HANDLE;
        }
    }
    
}


EVENT_HANDLE OpenBufferEvent(DS_HANDLE hStream)
{
    EVENT_HANDLE eventHand;
    tl.GCRegisterEvent(hStream, EVENT_NEW_BUFFER, &eventHand);
    //DSStartAcquisition(hStream, 0, GENTL_INFINITE);
    return eventHand;
}

void CloseBufferEvent(DS_HANDLE hStream)
{
    tl.GCUnregisterEvent(hStream, EVENT_NEW_BUFFER);
}

void CloseDataStream (DS_HANDLE hStream )
{
    if (GENTL_INVALID_HANDLE == hStream)
    {
        return;
    }

    tl.DSClose( hStream );
}

void CloseDevice(DEV_HANDLE hDevice )
{
    if (GENTL_INVALID_HANDLE == hDevice)
    {
        return;
    }

    tl.DevClose( hDevice );
}

void CloseInterface(IF_HANDLE hIface )
{
    if (GENTL_INVALID_HANDLE == hIface)
    {
        return;
    }

    tl.IFClose( hIface );
}

void CloseTL(TL_HANDLE hTL )
{
    if (GENTL_INVALID_HANDLE == hTL)
    {
        return;
    }

    tl.TLClose( hTL );
}

void CloseLib( void )
{
    tl.GCCloseLib( );
}

int32_t ReadGenTLValue(PORT_HANDLE hDev, uint64_t address, uint32_t* value)
{
    size_t size = sizeof(uint32_t);
    *value = 0;
    GC_ERROR err = tl.GCReadPort(hDev, address, value, &size);

    return err;
}

int32_t WriteGenTLValue(PORT_HANDLE hDev, uint64_t address, uint32_t value)
{
    size_t size = sizeof(uint32_t);
    GC_ERROR err = tl.GCWritePort(hDev, address, &value, &size);

    return err;
}

void splitString(const std::string &s, const char delim, std::vector<std::string> &elems)
{
    std::stringstream ss(s);
    std::string item;
    while (std::getline(ss, item, delim)) 
    {
        elems.push_back(item);
    }
}

void Test_XML(PORT_HANDLE hDev, const char* dev)
{
    const uint32_t MAX_CAM_XML_STRING_LENGTH = 256;
    const uint32_t DEVICE_XMLURL_REG = 0x00000018;

    size_t size = 4;
    size_t size2 = 4;

    
    uint32_t maxStrLength = MAX_CAM_XML_STRING_LENGTH;
    char xmlAddrString[MAX_CAM_XML_STRING_LENGTH] = {0};
    char xmlAddrString2[MAX_CAM_XML_STRING_LENGTH] = {0};

    size = MAX_CAM_XML_STRING_LENGTH;
    GC_ERROR err = tl.GCGetPortURL(hDev, xmlAddrString, &size);

    // size2 = MAX_CAM_XML_STRING_LENGTH;
    // INFO_DATATYPE iType;
    // GC_ERROR err2 = tl.GCGetPortURLInfo(hDev, 0, URL_INFO_URL, &iType, xmlAddrString2, &size2);

    if(err != GC_ERR_SUCCESS)
    {
        printf("Cann't read URL\n");
        return;
    }
    else
    {
        printf("URL: %s\n", xmlAddrString);
    }
    
    std::string xmlUrl(xmlAddrString);

    std::vector<std::string> xmlUrlSplit;
    splitString(xmlUrl, ';', xmlUrlSplit);
    
    uint64_t xmlFileSize = 0, xmlFileLocation = 0;
#ifdef _WIN32
    sscanf_s(xmlUrlSplit.at(1).c_str(), "%llx", &xmlFileLocation);   // read xml file address
    sscanf_s(xmlUrlSplit.at(2).c_str(), "%llx", &xmlFileSize);   // read xml file size
#else 
    sscanf(xmlUrlSplit.at(1).c_str(), "%lu", &xmlFileLocation);   // read xml file address
    sscanf(xmlUrlSplit.at(2).c_str(), "%lu", &xmlFileSize);   // read xml file size
#endif // _WIN32
    static const char* xmlExtXml = ".xml";
    static const char* xmlExtZip = ".zip";

    static const char* szKayaSampleDataEnv = "KAYA_VISION_POINT_SAMPLE_DATA";
    static const char* szKayaXmlFileName = "//GenTLTestXML";
    
#ifdef _WIN32
    char* kayaSampleDataEnv = NULL;
    size_t requiredSize;
    errno_t errno_env = _dupenv_s(&kayaSampleDataEnv, &requiredSize, szKayaSampleDataEnv);
#else 
    char* kayaSampleDataEnv = getenv(szKayaSampleDataEnv);
#endif //_WIN32
    std::string sKayaSampleDataEnv(kayaSampleDataEnv);
    std::string xmlOutFileName = sKayaSampleDataEnv + std::string(szKayaXmlFileName) + "_" + dev;

    if (std::string::npos != xmlUrlSplit.at(0).find(xmlExtXml))
    {
        xmlOutFileName += std::string(xmlExtXml);
        printf("Xml file path: %s\n", xmlOutFileName.c_str());
    }
    else if(std::string::npos != xmlUrlSplit.at(0).find(xmlExtZip))
    {
        xmlOutFileName += std::string(xmlExtZip);
        printf("Zip file path: %s\n", xmlOutFileName.c_str());
    }
    else
    {
        printf("Failed to find xml file extension\n\r");
        return;
    }

    char* xmlString = new char[xmlFileSize + 1];

    GC_ERROR err3 = tl.GCReadPort(hDev, xmlFileLocation, xmlString, &xmlFileSize);

    
    FILE* outFile = NULL;
#ifdef _WIN32
    
    fopen_s(&outFile, xmlOutFileName.c_str(), "wb");
#else
    outFile = fopen(xmlOutFileName.c_str(), "wb");
#endif //_WIN32
    
    if (outFile) // write to file only if it was opened
    {
        fwrite(xmlString, 1, xmlFileSize, outFile);
        fclose(outFile);
    }

    delete [] xmlString;
}

void Test_EventKill(EVENT_HANDLE eventHandle)
{
    tl.EventKill(eventHandle);
}

unsigned int event_thread_impl(void * pData)
{
    EventDataStruct* eventDataStruct = (EventDataStruct*)pData;
    EVENT_HANDLE eHandle = eventDataStruct->m_Hevent;

    uint8_t buffer[100];
    size_t bufferSize = sizeof(buffer);
    int counter = STREAM_CALLBACK_COUNT;

    GC_ERROR error;
    do {
        error = tl.EventGetData(eHandle, buffer, &bufferSize, GENTL_INFINITE);
        BUFFER_HANDLE bufferHandle = ((EVENT_NEW_BUFFER_DATA*)buffer)->BufferHandle;
        printf("Received event for buffer 0x%p with error=%d\n\r", bufferHandle, error);

        tl.DSQueueBuffer(eventDataStruct->m_hStream, bufferHandle);

    } while (
        (error == GC_ERR_SUCCESS)
        &&

#if (0==STREAM_CALLBACK_COUNT)
        (1)
#else
        (--counter > 0)
#endif
        );
    return 0;
}


void Test_AcquisitionStart(InterfaceInfo* pInterfaceInfo)
{
    if (pInterfaceInfo->hStream != GENTL_INVALID_HANDLE)
    {
        // data stream already allocated, first delete data stream
        return;
    }

    // create data stream
    pInterfaceInfo->hStream = OpenFirstDataStream(pInterfaceInfo->hDev);
    
    // allocated stream buffers
    OpenDataBuffer(pInterfaceInfo);

    // create stream event and thread
    pInterfaceInfo->hEvent = OpenBufferEvent(pInterfaceInfo->hStream);
    pInterfaceInfo->eventDataStruct.m_Hevent = pInterfaceInfo->hEvent;
    pInterfaceInfo->eventDataStruct.m_hStream = pInterfaceInfo->hStream;
    pInterfaceInfo->eventThread = std::thread(event_thread_impl, &pInterfaceInfo->eventDataStruct);


    tl.DSFlushQueue(pInterfaceInfo->hStream, ACQ_QUEUE_ALL_TO_INPUT);

    tl.DSStartAcquisition(pInterfaceInfo->hStream, 0, GENTL_INFINITE);

    // send "AcquisitionStart" to camera
    const uint32_t startAcquisitionReg = CAMERA_XML_ACQUISITION_START_VALUE;
    size_t startAcquisitionRegSize = sizeof(startAcquisitionReg);
    const uint64_t startAcquisitionRegAddr = CAMERA_XML_ACQUISITION_START_REG;


    tl.GCWritePort(pInterfaceInfo->hDevice, startAcquisitionRegAddr, &startAcquisitionReg, &startAcquisitionRegSize); // start acquisition
}

void Test_AcquisitionStop(InterfaceInfo* pInterfaceInfo)
{
    if (pInterfaceInfo->hStream == GENTL_INVALID_HANDLE)
    {
        // No data stream available
        return;
    }

    // send "AcquisitionStop" to camera
    const uint32_t stopAcquisitionReg = CAMERA_XML_ACQUISITION_STOP_VALUE;
    size_t stopAcquisitionRegSize = sizeof(stopAcquisitionReg);
    const uint64_t stopAcquisitionRegAddr = CAMERA_XML_ACQUISITION_STOP_REG;

    tl.GCWritePort(pInterfaceInfo->hDevice, stopAcquisitionRegAddr, &stopAcquisitionReg, &stopAcquisitionRegSize); // stop acquisition

    tl.DSStopAcquisition(pInterfaceInfo->hStream, 0);
    // tl.GCUnregisterEvent(newEvent, 1);
    tl.DSFlushQueue(pInterfaceInfo->hStream, ACQ_QUEUE_ALL_DISCARD);

    
    CloseBufferEvent(pInterfaceInfo->hStream);
    pInterfaceInfo->hEvent = GENTL_INVALID_HANDLE;

    // wait for eventThread to terminate
    std::cout << "eventThread's id: " << pInterfaceInfo->eventThread.get_id() << '\n';
    if (pInterfaceInfo->eventThread.joinable())
    {
        pInterfaceInfo->eventThread.join();
    }

    CloseDataBuffer(pInterfaceInfo);
    CloseDataStream(pInterfaceInfo->hStream);
    pInterfaceInfo->hStream = GENTL_INVALID_HANDLE;
}

struct ResourceReleaser
{
    ResourceReleaser(InterfaceInfo* pInterfaceInfo)
        : m_interfaceInfo(pInterfaceInfo)
    {
    }
    ~ResourceReleaser()
    {
        ReleaseInterface();

        CloseTL(hTL);
        hTL = GENTL_INVALID_HANDLE;

        CloseLib();
        ky_free_lib(hcti);
    }
    void ReleaseInterface()
    {
        Test_AcquisitionStop(m_interfaceInfo);

        CloseDevice(m_interfaceInfo->hDevice);
        m_interfaceInfo->hDevice = GENTL_INVALID_HANDLE;

        CloseInterface(m_interfaceInfo->hIface);
        m_interfaceInfo->hIface = GENTL_INVALID_HANDLE;
    }

    InterfaceInfo* m_interfaceInfo;

}; // struct ResourceReleaser

struct OpenScopeQuard
{
    OpenScopeQuard(ResourceReleaser& handlesReleaser)
        : m_refHandlesReleaser(handlesReleaser)
        , m_ScopeSucceeded(false)
    { }

    ~OpenScopeQuard()
    {
        if (!m_ScopeSucceeded)
        {
            m_refHandlesReleaser.ReleaseInterface();
        }
    }

    ResourceReleaser& m_refHandlesReleaser;
    bool m_ScopeSucceeded;
};

int main(int argc, char* argv[])
{
    GC_ERROR ret_code;
    char choice = 0;

    // Automatically release resources when this scope exits:
    ResourceReleaser resourceReleaser(&g_intefaceInfo);

    if (!InitLib())
    {
        return -1;
    }

    hTL = OpenTL();

    size_t bufferSize = MAX_PATH;
    INFO_DATATYPE piType;
    char buffer[MAX_PATH];

    tl.TLGetInfo(hTL, TL_INFO_VENDOR, &piType, buffer, &bufferSize); //TL_INFO_DISPLAYNAME
    printf("============%s============\n\r", buffer);

    PrintHelp();
    PrintDevices(hTL);

    printf("\nGenTL>");
    while(choice != 'e')
    {
        Sleep(1);
        if(_kbhit())
        {
            choice=getchar();
            //printf("\nGenTL>%c\n", choice);
            if (choice >= '0' && choice <= '7') // Open selected interface
            {
                resourceReleaser.ReleaseInterface(); // release old interface

                OpenScopeQuard openScopeQuard(resourceReleaser);

                interfaceIndex = choice - '0';
                printf("Openning interface #%d\n", interfaceIndex);
                
                g_intefaceInfo.hIface = OpenInterface(hTL);
                if (!g_intefaceInfo.hIface)
                {
                    printf("Failed to find Frame Grabber\n");

                    getchar();
                    continue;
                }
                printf("Successfully found Frame Grabber\n");

                g_intefaceInfo.hDev = OpenFirstDevice(g_intefaceInfo.hIface);
                if (!g_intefaceInfo.hDev)
                {
                    printf("Failed to find remote device\n");

                    getchar();
                    continue;
                }

                tl.DevGetPort(g_intefaceInfo.hDev, &g_intefaceInfo.hDevice);
                if (!g_intefaceInfo.hDevice)
                {
                    printf("Failed to find Camera\n");

                    getchar();
                    continue;
                }
                printf("Successfully found Camera\n");

                openScopeQuard.m_ScopeSucceeded = true;

            }//if (choice >= '0' && choice <= '7')
            else
            switch (choice)
            {
            case '?': 
                PrintHelp();
                break;
            case 'l': // Close interface
                resourceReleaser.ReleaseInterface();
                break;
            case 'g': // Test_XML(hIface) (grabber)
                Test_XML(g_intefaceInfo.hIface, "Grabber");
                break;
            case 'x': // Test_XML(hDevice) (camera)
                Test_XML(g_intefaceInfo.hDevice, "Camera");
                break;
            case 'r': // ReadGenTLValue
            {
                uint64_t address = 0;
                uint32_t value = 0;
                size_t size = 0;

                printf("Address(hex): ");
                std::cin >> std::hex >> address;
                ret_code = ReadGenTLValue(g_intefaceInfo.hDevice, address, &value);
                if (ret_code == GC_ERR_SUCCESS)
                {
                    printf("Successfully reg read value(dec) = %d\n", value);
                }
                else
                {
                    printf("Reg read error = %d\n", ret_code);
                }
                break;
            }
            case 'w': // WriteGenTLValue
            {
                uint64_t address = 0;
                uint32_t value = 0;
                size_t size = 0;

                printf("Address(hex): ");
                std::cin >> std::hex >> address;
                printf("value(dec): ");
                std::cin >> std::dec >> value;
                ret_code = WriteGenTLValue(g_intefaceInfo.hDevice, address, value);
                if (ret_code == GC_ERR_SUCCESS)
                {
                    printf("Successfully reg write value(dec) = %d\n", value);
                }
                else
                {
                    printf("Reg write error = %d\n", ret_code);
                }
                break;
            }

#ifndef BLOCK_STREAM
            case 'k': // Test_EventKill
                Test_EventKill(g_intefaceInfo.hEvent);
                break;

            case 't': // "AcquisitionStop"
            {
                Test_AcquisitionStop(&g_intefaceInfo);
                break;
            }
            case 's': // "AcquisitionStart"
            {
                Test_AcquisitionStart(&g_intefaceInfo);
                break;
            }
#endif
            default:
                break;
            }//switch (choice)

            printf("\nGenTL>");

        }//if(_kbhit())
    }//while(choice != 'e')

    // resourceReleaser will release all opened handles upon exiting

    return 0;
}

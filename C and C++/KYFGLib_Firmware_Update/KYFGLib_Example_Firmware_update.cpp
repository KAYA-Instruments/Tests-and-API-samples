
//#include "stdafx.h"

#include <stdio.h>
#include <map>
#include <iostream>
#include <string>
#include <vector>
#include <algorithm>
#include "KYFGLib.h"

#ifdef __linux__
#include <cstring> // memset
#endif

#if !defined(_countof)
#define _countof(_Array) (sizeof(_Array) / sizeof(_Array[0]))
#endif

#ifdef __linux__ // _aligned_malloc() implementation for __linux__
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



#define MAXBOARDS 4
#define MAX_FILENAME_LENGTH 256
FGHANDLE m_FgHandles[MAXBOARDS];
UPDATE_STATUS updateStatus;
int nKayaDevicesCount = 0;
KY_DEVICE_INFO* grabbersInfoArray = NULL;
unsigned int currentGrabberIndex;
std::string updateFilePath;

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
void Close(int returnCode)
{
    printf("Input any char to exit\n");
    BlockingInput();
    exit(returnCode);
}

void CharInput(char expected_char, const char* error_str)
{
    int valid = 0;
    char c;

    while (!valid)
    {
        c = BlockingInput();

        valid = expected_char == c;

        if (!valid)
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

    while (!valid)
    {
        c = BlockingInput();

        *value = c - '0';

        valid = *value >= min && *value <= max;

        if (!valid)
        {
            printf("%s", error_str);
        }
        else
        {
            break;
        }
    }
}

int ConnectToGrabber(unsigned int grabberIndex)
{

    if ((m_FgHandles[grabberIndex] = KYFG_Open(grabberIndex)) != -1) // Connect to selected device
    {
        printf("Good connection to grabber #%d, m_FgHandles=%X\n", grabberIndex, m_FgHandles[grabberIndex]);
    }
    else
    {
        printf("Could not connect to grabber #%d\n", grabberIndex);
        BlockingInput();
        return 0;
    }

    currentGrabberIndex = grabberIndex;



    return 1;
}


int setPathToUpdateFile()
{
    std::cout << "Please set full path to update file: ";
    std::cin.get();
    std::getline(std::cin, updateFilePath);
    
    std::cout << "You write " << updateFilePath << std::endl;

    return 0;
}
int checkUpdateFile()
{
    KYFG_UPDATE_FILE updateFileSrtuct;
    updateFileSrtuct.version = 1;
    FGSTATUS res;
    res = KYFG_GetFirmareUpdateFileInfo(m_FgHandles[currentGrabberIndex], updateFilePath.c_str(), &updateFileSrtuct);
    if (FGSTATUS_OK != res)
    {
        printf("Error while check update file\nError code: %x", res);
        return -1;
    }
    std::cout << "File successfully checked" << std::endl;
    printf("FlashMinorRev       %d\n", updateFileSrtuct.flashMinorRev );
    printf("FlashMajorRev       %d\n", updateFileSrtuct.flashMajorRev );
    printf("FileMinorRev        %d\n", updateFileSrtuct.fileMinorRev );
    printf("FileMajorRev        %d\n", updateFileSrtuct.fileMajorRev);
    printf("FlashVendorId       %d\n", updateFileSrtuct.flashVendorId);
    printf("FlashBoardId        %d\n", updateFileSrtuct.flashBoardId);
    printf("FileVendorId        %d\n", updateFileSrtuct.fileVendorId);
    printf("FileBoardId         %d\n", updateFileSrtuct.fileBoardId);
    printf("FlashVersion        %d\n", updateFileSrtuct.flashVersion);
    printf("FlashTimeStamp      %d\n", updateFileSrtuct.flashTimeStamp);
    printf("FileVersion         %d\n", updateFileSrtuct.fileVersion);
    printf("FileTimeStamp       %d\n", updateFileSrtuct.fileTimeStamp);
    return 0;
}

KYBOOL updateCallback(const UPDATE_STATUS* UpdateStatus, void* context)
{
    printf("\n\nPROCESS CALLBACK FUNCTION\n");
    printf("Update struct version %d\n", UpdateStatus->struct_version);
    printf("%s new firmware\n", UpdateStatus->is_writing ? "writing" : "validating");
#ifdef __linux__
    printf("Bytes sent %lu\n", UpdateStatus->bytes_sent);
    printf("Total size %lu\n", UpdateStatus->total_size);
#else
    printf("Bytes sent %llu\n", UpdateStatus->bytes_sent);
    printf("Total size %llu\n", UpdateStatus->total_size);
#endif // WIN32
    


    return KYTRUE;
}

int printHelp()
{
    std::cout << "Available parameters:" << std::endl;
    std::cout << "--unattended:     0-Disable 1-Enable; " << std::endl;
    std::cout << "--device_index:   delect grabber ingex if unattended mode enable" << std::endl;
    std::cout << "--filePath:       path to binary file unattended mode enable" << std::endl;
    std::cout << "--help --h:       print help" << std::endl;
    return 0;
}
/*
This code is inspired by https://stackoverflow.com/a/868894/1468415
The class InputParser is used for parsing command line arguments
*/
class InputParser
{
public:
    InputParser()
    {
    }
    typedef std::initializer_list<std::pair<const std::string, std::string>> InitilizerList;
    InputParser(const InitilizerList & _list)
        :m_mapOptions(_list)
    {
    }

    void ReadOptions(int &argc, char **argv)
    {
        for (int i = 0; i < argc; i += 1)
        {
            if ((strcmp(argv[i], "--help" ) == 0) || (strcmp(argv[i], "--h" ) == 0))
            {
                printHelp();
                Close(0);
            }
        }
        for (int i = 1; (i + 1) < argc; i += 2)
        {
            m_mapOptions[argv[i]] = argv[i + 1];
        }
    }

    void PrintOptions() const
    {
        for (const auto& n : m_mapOptions)
        {
            std::cout << n.first << " = " << n.second << "; ";
        }
        std::cout << std::endl;
    }

    const std::string& getCmdOption(const std::string &option) const
    {
        static const std::string empty_string("");
        try
        {
            return m_mapOptions.at(option);
        }
        catch (...)
        {
            return empty_string;
        }
    }

    bool cmdOptionExists(const std::string &option) const
    {
        return m_mapOptions.count(option) > 0;
    }
private:
    std::map<std::string, std::string> m_mapOptions;
}; // class InputParser 

int main(int argc, char **argv)
{
    InputParser options
    (
        {
            {"--unattended",            "0"},      // 0-False 1-true
            {"--device_index",          "0"},      // use 0-th PCI device
            {"--filePath",              "" },      // path to binary file       
        }
    );
    
    options.ReadOptions(argc, argv);
    options.PrintOptions();
    KYFGLib_InitParameters kyInit;
    KYBOOL isUnnattended;
    // "--unattended"
    const std::string &sunattended = options.getCmdOption("--unattended");
    if (!sunattended.empty())
    {
        isUnnattended = std::stoi(sunattended);
    }
    if (isUnnattended)
    {
        std::cout << "Script starts in unattended mode !!!" << std::endl;
        // "--filePath"
        updateFilePath = options.getCmdOption("--filePath");
        std::cout << "Update File " << updateFilePath << std::endl;
        // "--device_index"
        const std::string &sdeviceIndex = options.getCmdOption("--device_index");
        if (!sdeviceIndex.empty())
        {
            currentGrabberIndex = std::stoi(sdeviceIndex);
            std::cout << "Grabber index " << currentGrabberIndex << std::endl;
        }
    }


    // Initialize library
    
    memset(&kyInit, 0, sizeof(kyInit));
    kyInit.version = 2;
    kyInit.concurrency_mode = 0;
 
    int grabberIndex = 0;
    kyInit.logging_mode = 0;
    kyInit.noVideoStreamProcess = KYFALSE;
    char c = 0;

    if (FGSTATUS_OK != KYFGLib_Initialize(&kyInit))
    {
        printf("Library initialization failed \n ");
        Close(-1);
    }
    for (int i = 0; i < MAXBOARDS; i++)
    {
        m_FgHandles[i] = INVALID_FGHANDLE;
    }
    // Scan for grabbers

    KY_DeviceScan(&nKayaDevicesCount);    // Retrieve the number of virtual and hardware devices connected to PC
    if (!nKayaDevicesCount)
    {
        printf("No PCI devices found\n");
        Close(0);
    }
    grabbersInfoArray = new KY_DEVICE_INFO[nKayaDevicesCount];

    for (int i = 0; i < nKayaDevicesCount; i++)
    {
        grabbersInfoArray[i].version = KY_MAX_DEVICE_INFO_VERSION;
        if (FGSTATUS_OK != KY_DeviceInfo(i, &grabbersInfoArray[i]))
        {
            printf("Wasn't able to retrive information from device #%d\n", i);
            continue;
        }
    }
    // Select and open grabber

    KYBOOL grabberReady = KYFALSE;

    while (!grabberReady)
    {
        // Select framegrabber

        printf("Select and open grabber:\n");
        for (int i = 0; i < nKayaDevicesCount; i++)
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
        if (isUnnattended)
        {
            grabberIndex = currentGrabberIndex;
        } 
        else
        {
            while (!inputValid)
            {
                NumberInRangeInput(0, nKayaDevicesCount - 1, &grabberIndex, "Invalid index\n");

                printf("Selected grabber #%d\n", grabberIndex);
                inputValid = KYTRUE;
                break;
            }
        }
        // Connect to framegrabber

        if (ConnectToGrabber(grabberIndex))
        {
            grabberReady = KYTRUE;
            break;
        }
    }
    if (isUnnattended)
    {
        std::cout << "Choosed update file " << updateFilePath.c_str() << std::endl;
        checkUpdateFile();
        printf("Firmware update started\n");
        FGSTATUS updateResult;
        updateResult = KYFG_LoadFirmware(m_FgHandles[currentGrabberIndex], updateFilePath.c_str(), updateCallback, NULL);
        if (updateResult != FGSTATUS_OK)
        {
            printf("ERROR while firmware update\nError codeL %x\n", updateResult);
        }
        else
        {
            printf("Firmware successfully updated\nPlease shut down to your computer");
        }
    }
    else 
    {
        while (c != 'e')
        {
            printf("\nSelect option:\n");
            printf("[p] set path to update file\n");
            printf("[c] Check update file\n");
            printf("[s] start update\n");
            printf("[e] Exit\n");

            c = BlockingInput();

            if ('p' == c)
            {
                setPathToUpdateFile();
                std::cout << "Choosed update file " << updateFilePath.c_str() << std::endl;
            }
            else if ('c' == c)
            {
                if (updateFilePath.length() == 0)
                {
                    printf("Update file not choosed\n");
                    continue;
                }
                checkUpdateFile();
            }
            else if ('s' == c)
            {
                printf("Firmware update started\n");
                FGSTATUS updateResult;
                updateResult = KYFG_LoadFirmware(m_FgHandles[currentGrabberIndex], updateFilePath.c_str(), updateCallback,  NULL);
                if (updateResult != FGSTATUS_OK)
                {
                    printf("ERROR while firmware update\nError codeL %x\n", updateResult);
                }
                else
                {
                    std::cout << "Firmware successfully updated" << std::endl << "Please shut down your computer" << std::endl << std::endl;
                }
            }
        }
    }

    KYFG_Close(m_FgHandles[grabberIndex]);
    Close(0);
}


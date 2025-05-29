#ifndef KY_DRIVER_GENTL_H_
#define KY_DRIVER_GENTL_H_
#include "ky_os.h"
#include "GenTL_v1_5.h"
using namespace GenTL;

struct tl_calls
{
    ky_fn_declare(GCGetInfo)
    ky_fn_declare(GCGetLastError)
    ky_fn_declare(GCInitLib)
    ky_fn_declare(GCCloseLib)
    ky_fn_declare(GCReadPort)
    ky_fn_declare(GCWritePort)
    ky_fn_declare(GCGetPortURL)
    ky_fn_declare(GCGetPortInfo)
    ky_fn_declare(GCRegisterEvent)
    ky_fn_declare(GCUnregisterEvent)
    ky_fn_declare(EventGetData)
    ky_fn_declare(EventGetDataInfo)
    ky_fn_declare(EventGetInfo)
    ky_fn_declare(EventFlush)
    ky_fn_declare(EventKill)
    ky_fn_declare(TLOpen)
    ky_fn_declare(TLClose)
    ky_fn_declare(TLGetInfo)
    ky_fn_declare(TLGetNumInterfaces)
    ky_fn_declare(TLGetInterfaceID)
    ky_fn_declare(TLGetInterfaceInfo)
    ky_fn_declare(TLOpenInterface)
    ky_fn_declare(TLUpdateInterfaceList)
    ky_fn_declare(IFClose)
    ky_fn_declare(IFGetInfo)
    ky_fn_declare(IFGetNumDevices)
    ky_fn_declare(IFGetDeviceID)
    ky_fn_declare(IFUpdateDeviceList)
    ky_fn_declare(IFGetDeviceInfo)
    ky_fn_declare(IFOpenDevice)
    ky_fn_declare(DevGetPort)
    ky_fn_declare(DevGetNumDataStreams)
    ky_fn_declare(DevGetDataStreamID)
    ky_fn_declare(DevOpenDataStream)
    ky_fn_declare(DevGetInfo)
    ky_fn_declare(DevClose)
    ky_fn_declare(DSAnnounceBuffer)
    ky_fn_declare(DSAllocAndAnnounceBuffer)
    ky_fn_declare(DSFlushQueue)
    ky_fn_declare(DSStartAcquisition)
    ky_fn_declare(DSStopAcquisition)
    ky_fn_declare(DSGetInfo)
    ky_fn_declare(DSGetBufferID)
    ky_fn_declare(DSClose)
    ky_fn_declare(DSRevokeBuffer)
    ky_fn_declare(DSQueueBuffer)
    ky_fn_declare(DSGetBufferInfo)
    ky_fn_declare(GCGetNumPortURLs)
    ky_fn_declare(GCGetPortURLInfo)
    ky_fn_declare(GCReadPortStacked)
    ky_fn_declare(GCWritePortStacked)
    ky_fn_declare(DSGetBufferChunkData)
    ky_fn_declare(IFGetParentTL)
    ky_fn_declare(DevGetParentIF)
    ky_fn_declare(DSGetParentDev)
    ky_fn_declare(DSGetNumBufferParts)
    ky_fn_declare(DSGetBufferPartInfo)
};
/* Structure to hold function pointers for GenTL API calls */


/* Helper to load all GenTL API call symbols from the cti - needed for reuse.
* Macro rather than function because of the side-effects (includes test
* statements expected to be executed within the test procedure. */
#define LOAD_SYMBOLS(_tl_, _hcti_) \
  ky_fn_load (_tl_, _hcti_, GCGetInfo) \
  ky_fn_load (_tl_, _hcti_, GCGetLastError) \
  ky_fn_load (_tl_, _hcti_, GCInitLib) \
  ky_fn_load (_tl_, _hcti_, GCCloseLib) \
  ky_fn_load (_tl_, _hcti_, GCReadPort) \
  ky_fn_load (_tl_, _hcti_, GCWritePort) \
  ky_fn_load (_tl_, _hcti_, GCGetPortURL) \
  ky_fn_load (_tl_, _hcti_, GCGetPortInfo) \
  ky_fn_load (_tl_, _hcti_, GCRegisterEvent) \
  ky_fn_load (_tl_, _hcti_, GCUnregisterEvent) \
  ky_fn_load (_tl_, _hcti_, EventGetData) \
  ky_fn_load (_tl_, _hcti_, EventGetDataInfo) \
  ky_fn_load (_tl_, _hcti_, EventGetInfo) \
  ky_fn_load (_tl_, _hcti_, EventFlush) \
  ky_fn_load (_tl_, _hcti_, EventKill) \
  ky_fn_load (_tl_, _hcti_, TLOpen) \
  ky_fn_load (_tl_, _hcti_, TLClose) \
  ky_fn_load (_tl_, _hcti_, TLGetInfo) \
  ky_fn_load (_tl_, _hcti_, TLGetNumInterfaces) \
  ky_fn_load (_tl_, _hcti_, TLGetInterfaceID) \
  ky_fn_load (_tl_, _hcti_, TLGetInterfaceInfo) \
  ky_fn_load (_tl_, _hcti_, TLOpenInterface) \
  ky_fn_load (_tl_, _hcti_, TLUpdateInterfaceList) \
  ky_fn_load (_tl_, _hcti_, IFClose) \
  ky_fn_load (_tl_, _hcti_, IFGetInfo) \
  ky_fn_load (_tl_, _hcti_, IFGetNumDevices) \
  ky_fn_load (_tl_, _hcti_, IFGetDeviceID) \
  ky_fn_load (_tl_, _hcti_, IFUpdateDeviceList) \
  ky_fn_load (_tl_, _hcti_, IFGetDeviceInfo) \
  ky_fn_load (_tl_, _hcti_, IFOpenDevice) \
  ky_fn_load (_tl_, _hcti_, DevGetPort) \
  ky_fn_load (_tl_, _hcti_, DevGetNumDataStreams) \
  ky_fn_load (_tl_, _hcti_, DevGetDataStreamID) \
  ky_fn_load (_tl_, _hcti_, DevOpenDataStream) \
  ky_fn_load (_tl_, _hcti_, DevGetInfo) \
  ky_fn_load (_tl_, _hcti_, DevClose) \
  ky_fn_load (_tl_, _hcti_, DSAnnounceBuffer) \
  ky_fn_load (_tl_, _hcti_, DSAllocAndAnnounceBuffer) \
  ky_fn_load (_tl_, _hcti_, DSFlushQueue) \
  ky_fn_load (_tl_, _hcti_, DSStartAcquisition) \
  ky_fn_load (_tl_, _hcti_, DSStopAcquisition) \
  ky_fn_load (_tl_, _hcti_, DSGetInfo) \
  ky_fn_load (_tl_, _hcti_, DSGetBufferID) \
  ky_fn_load (_tl_, _hcti_, DSClose) \
  ky_fn_load (_tl_, _hcti_, DSRevokeBuffer) \
  ky_fn_load (_tl_, _hcti_, DSQueueBuffer) \
  ky_fn_load (_tl_, _hcti_, DSGetBufferInfo) \
  ky_fn_load (_tl_, _hcti_, GCGetNumPortURLs) \
  ky_fn_load (_tl_, _hcti_, GCGetPortURLInfo) \
  ky_fn_load (_tl_, _hcti_, GCReadPortStacked) \
  ky_fn_load (_tl_, _hcti_, GCWritePortStacked) \
  ky_fn_load (_tl_, _hcti_, DSGetBufferChunkData) \
  ky_fn_load (_tl_, _hcti_, IFGetParentTL) \
  ky_fn_load (_tl_, _hcti_, DevGetParentIF) \
  ky_fn_load (_tl_, _hcti_, DSGetParentDev) \
  ky_fn_load (_tl_, _hcti_, DSGetNumBufferParts) \
  ky_fn_load (_tl_, _hcti_, DSGetBufferPartInfo)

/* Its counterpart for symmetry */
#define FREE_SYMBOLS(_tl_) memset (&_tl_, 0, sizeof(_tl_));

#endif //KY_DRIVER_GENTL_H_

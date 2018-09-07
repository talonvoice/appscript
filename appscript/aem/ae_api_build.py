# CFFI implementation of the API surface provided by oldschool py-appscript's ae.c

import cffi

ffi = cffi.FFI()
ffi.cdef(r'''
typedef bool Boolean;
typedef int32_t OSAError;
typedef int32_t OSErr;
typedef int32_t OSStatus;
typedef int32_t SInt32;
typedef long Size;
typedef uint8_t UInt8;
typedef uint32_t UInt32;

typedef void *CFTypeRef;
typedef CFTypeRef CFAllocatorRef;
typedef CFTypeRef CFArrayRef;
typedef CFTypeRef CFDataRef;
typedef CFTypeRef CFDictionaryRef;
typedef CFTypeRef CFStringRef;
typedef CFTypeRef CFURLRef;
typedef signed long long CFIndex;
typedef uint32_t CFStringEncoding;

typedef uint32_t FourCharCode;
typedef FourCharCode OSType;
typedef FourCharCode DescType;
typedef uint32_t ProcessApplicationTransformState;
typedef struct { uint8_t hidden[80]; } FSRef;

typedef struct {
    DescType descriptorType;
    void *dataHandle;
} AEDesc;
typedef FourCharCode AEKeyword;
typedef SInt32 AESendMode;
typedef AEDesc AEDescList;
typedef AEDescList AERecord;
typedef AEDesc AEAddressDesc;
typedef AERecord AppleEvent;
typedef AppleEvent *AppleEventPtr;
typedef int16_t AEReturnID;
typedef int32_t AETransactionID;
typedef uint32_t AEEventClass;
typedef uint32_t AEEventID;
typedef int8_t AEArrayType;

typedef struct {
    CFIndex version;
    uint32_t flags;
    const FSRef *application;
    void *asyncLaunchRefCon;
    CFDictionaryRef environment;

    CFArrayRef argv;
    AppleEvent *initialEvent;
} LSApplicationParameters;
typedef struct { uint32_t highLongOfPSN, lowLongOfPSN; } ProcessSerialNumber;

CFStringRef CFStringCreateWithCString(CFAllocatorRef alloc, const char *cStr, CFStringEncoding encoding);
const UInt8 *CFDataGetBytePtr(CFDataRef theData);
CFIndex CFDataGetLength(CFDataRef theData);
void CFRelease(CFTypeRef cf);

Boolean AECheckIsRecord(const AEDesc *theDesc);
OSErr AECoerceDesc(const AEDesc *theAEDesc, DescType toType, AEDesc *result);
OSErr AECountItems(const AEDescList *theAEDescList, long *theCount);
OSErr AECreateAppleEvent(AEEventClass theAEEventClass, AEEventID theAEEventID, const AEAddressDesc *target, AEReturnID returnID, AETransactionID transactionID, AppleEvent *result);
OSErr AECreateDesc(DescType typeCode, const void *dataPtr, Size dataSize, AEDesc *result);
OSErr AECreateList(const void *factoringPtr, Size factoredSize, Boolean isRecord, AEDescList *resultList);
OSErr AEDisposeDesc(AEDesc *theAEDesc);
OSErr AEGetAttributeDesc(const AppleEvent *theAppleEvent, AEKeyword theAEKeyword, DescType desiredType, AEDesc *result);
OSErr AEGetDescData(const AEDesc *theAEDesc, void *dataPtr, Size maximumSize);
OSErr AEGetNthDesc(const AEDescList *theAEDescList, long index, DescType desiredType, AEKeyword *theAEKeyword, AEDesc *result);
OSErr AEGetParamDesc(const AppleEvent *theAppleEvent, AEKeyword theAEKeyword, DescType desiredType, AEDesc *result);
OSErr AEPutAttributeDesc(AppleEvent *theAppleEvent, AEKeyword theAEKeyword, const AEDesc *theAEDesc);
OSErr AEPutDesc(AEDescList *theAEDescList, long index, const AEDesc *theAEDesc);
OSErr AEPutParamDesc(AppleEvent *theAppleEvent, AEKeyword theAEKeyword, const AEDesc *theAEDesc);
OSStatus AESendMessage(const AppleEvent *event, AppleEvent *reply, AESendMode sendMode, long timeOutInTicks);
Size AEGetDescDataSize(const AEDesc *theAEDesc);
OSAError OSACopyScriptingDefinition(const FSRef *ref, SInt32 modeFlags, CFDataRef *sdef);

OSStatus TransformProcessType(const ProcessSerialNumber *psn, ProcessApplicationTransformState transformState);
OSErr GetNextProcess(ProcessSerialNumber *psn);
OSStatus GetProcessBundleLocation(const ProcessSerialNumber *psn, FSRef *location);
const char *GetMacOSStatusErrorString(OSStatus err);
const char *GetMacOSStatusCommentString(OSStatus err);

OSStatus FSPathMakeRef(const UInt8 *path, FSRef *ref, Boolean *isDirectory);
OSErr FSCompareFSRefs(const FSRef *ref1, const FSRef *ref2);
OSStatus FSRefMakePath(const FSRef *ref, UInt8 *path, UInt32 pathBufferSize);

OSStatus LSOpenApplication(const LSApplicationParameters *appParams, ProcessSerialNumber *outPSN);
OSStatus LSFindApplicationForInfo(OSType inCreator, CFStringRef inBundleID, CFStringRef inName, FSRef *outAppRef, CFURLRef *outAppURL);
''', packed=1)
ffi.set_source('ae_api', None)
ffi.emit_python_code('ae_api.py')

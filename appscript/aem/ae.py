# CFFI implementation of the API surface provided by oldschool py-appscript's ae.c

import cffi
import os
import struct
import sys

py3 = sys.version_info[0] >= 3
if py3:
    from urllib.parse import urlparse
    from urllib.request import pathname2url
else:
    from urlparse import urlparse
    from urllib import pathname2url

kCFURLPOSIXPathStyle = 0
kCFStringEncodingUTF8 = 0x08000100
PATH_MAX = 1024
kNoProcess = 0
kCurrentProcess = 2
kAutoGenerateReturnID = -1
kAnyTransactionID = 0
typeProcessSerialNumber = b'psn '
kProcessTransformToForegroundApplication = 1
kProcessTransformToBackgroundApplication = 2
kProcessTransformToUIElementApplication = 4

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
lib = ffi.dlopen('/System/Library/Frameworks/Carbon.framework/Carbon')

class MacOSError(Exception):
    def __init__(self, code):
        self.code = code

    def __str__(self):
        name, comment = stringsforosstatus(self.code)
        return "\"{}\" ({})".format(name, self.code)

def throw(errno):
    if errno != 0:
        raise MacOSError(errno)

def CFString(s):
    if s is None: return ffi.NULL
    return lib.CFStringCreateWithCString(ffi.NULL, s.encode('utf8'), kCFStringEncodingUTF8);

# TODO: FSRef is deprecated
def FSRef(path):
    fs_ref = ffi.new('FSRef *')
    throw(lib.FSPathMakeRef(path.encode('utf8'), fs_ref, ffi.NULL))
    return fs_ref

ostype = struct.Struct('>I')
def unpack_ostype(ot): return ostype.pack(ot)
def pack_ostype(s): return ostype.unpack(s)[0]

class AEDesc:
    def __init__(self):
        self.handle = ffi.new('AEDesc *')

    def __del__(self):
        lib.AEDisposeDesc(self.handle)

    @property
    def type(self): return unpack_ostype(self.handle.descriptorType)

    @property
    def data(self):
        size = lib.AEGetDescDataSize(self.handle)
        buf = ffi.new('char[]', size)
        throw(lib.AEGetDescData(self.handle, buf, size))
        return ffi.buffer(buf)[:]

    def coerce(self, to):
        result = AEDesc()
        throw(lib.AECoerceDesc(self.handle, pack_ostype(to), result.handle))
        return result

    def count(self):
        count = ffi.new('long *')
        throw(lib.AECountItems(self.handle, count))
        return count[0]

    def isrecord(self):
        return bool(lib.AECheckIsRecord(self.handle))

    def setitem(self, i, desc):
        if not isinstance(desc, AEDesc):
            raise TypeError('desc must be an AEDesc')
        throw(lib.AEPutDesc(self.handle, i, desc.handle))

    def getitem(self, i, typ):
        key = ffi.new('AEKeyword *')
        result = AEDesc()
        throw(lib.AEGetNthDesc(self.handle, i, pack_ostype(typ), key, result.handle))
        ot = unpack_ostype(key[0])
        return ot, result

    def setparam(self, key, desc):
        if not isinstance(desc, AEDesc):
            raise TypeError('desc must be an AEDesc')
        throw(lib.AEPutParamDesc(self.handle, pack_ostype(key), desc.handle))

    def getparam(self, key, typ):
        result = AEDesc()
        throw(lib.AEGetParamDesc(self.handle, pack_ostype(key), pack_ostype(typ), result.handle))
        return result

    def setattr(self, key, desc):
        if not isinstance(desc, AEDesc):
            raise TypeError('desc must be an AEDesc')
        throw(lib.AEPutAttributeDesc(self.handle, pack_ostype(key), desc.handle))

    def getattr(self, key, typ):
        result = AEDesc()
        throw(lib.AEGetAttributeDesc(self.handle, pack_ostype(key), pack_ostype(typ), result.handle))
        return result

    def send(self, mode, timeout):
        reply = AEDesc()
        throw(lib.AESendMessage(self.handle, reply.handle, mode, timeout))
        return reply

def newdesc(typ, buf):
    result = AEDesc()
    throw(lib.AECreateDesc(pack_ostype(typ), buf, len(buf), result.handle))
    return result

def newlist():
    result = AEDesc()
    throw(lib.AECreateList(ffi.NULL, 0, 0, result.handle))
    return result

def newrecord():
    result = AEDesc()
    throw(lib.AECreateList(ffi.NULL, 0, 1, result.handle))
    return result

def newappleevent(event_cls, event_id, target, return_id=kAutoGenerateReturnID, transaction_id=kAnyTransactionID):
    if not isinstance(target, AEDesc):
        raise TypeError('target must be an AEDesc')
    result = AEDesc()
    throw(lib.AECreateAppleEvent(pack_ostype(event_cls), pack_ostype(event_id), target.handle,
                                 return_id, transaction_id, result.handle))
    return result

def stringsforosstatus(errno):
    err = ffi.string(lib.GetMacOSStatusErrorString(errno)).decode('utf8')
    comment = ffi.string(lib.GetMacOSStatusCommentString(errno)).decode('utf8')
    return (err, comment)

def convertpathtourl(path, style):
    if style != kCFURLPOSIXPathStyle:
        raise ValueError('only kCFURLPOSIXPathStyle is supported')
    if path.startswith('/'):
        return "file://{}".format(pathname2url(path))
    return os.path.normpath(path)

def converturltopath(url, style):
    if style != kCFURLPOSIXPathStyle:
        raise ValueError('only kCFURLPOSIXPathStyle is supported')
    return urlparse(url).path

# TODO: LSFindApplicationForInfo is deprecated in favor of LSCopyApplicationURLsForBundleIdentifier
def findapplicationforinfo(creator, bundle, name):
    bundle = CFString(bundle)
    name = CFString(name)
    app_ref = ffi.new('FSRef *')
    errno = lib.LSFindApplicationForInfo(pack_ostype(creator), bundle, name, app_ref, ffi.NULL)
    if bundle: lib.CFRelease(bundle)
    if name: lib.CFRelease(name)
    throw(errno)
    path = ffi.new('char[]', PATH_MAX)
    lib.FSRefMakePath(app_ref, path, PATH_MAX)
    return ffi.string(path).decode('utf8')

# TODO: This returns an AEDesc from an application path.
# This approach is a bit gnarly. There are certainly newer apis for this.
def psnforapplicationpath(path):
    app_ref = FSRef(path)
    psn = ffi.new('ProcessSerialNumber *')
    psn[0] = (0, kNoProcess)
    found = ffi.new('FSRef *')
    while True:
        throw(lib.GetNextProcess(psn))
        throw(lib.GetProcessBundleLocation(psn, found))
        if lib.FSCompareFSRefs(app_ref, found) == 0:
            break
    return newdesc(typeProcessSerialNumber, ffi.buffer(psn, ffi.sizeof(psn))[:])

_nulldesc = newdesc(typeProcessSerialNumber, struct.pack('II', 0, kNoProcess))
_noopevent = newappleevent(b'ascr', b'noop', _nulldesc)
# TODO: LSOpenApplication is deprecated, FSRef is deprecated
def launchapplication(path, first_event=_noopevent, flags=0):
    if not isinstance(first_event, AEDesc):
        raise TypeError('first_event must be an AEDesc')
    app_ref = FSRef(path)
    params = ffi.new('LSApplicationParameters *')
    params[0] = (0, flags, app_ref, ffi.NULL, ffi.NULL, ffi.NULL, first_event.handle)
    psn = ffi.new('ProcessSerialNumber *')
    throw(lib.LSOpenApplication(params, psn))
    return newdesc(typeProcessSerialNumber, ffi.buffer(psn, ffi.sizeof(psn))[:])

# this is used to transform our own process, just to pop up an error dialog
def transformprocesstoforegroundapplication():
    psn = ffi.new('ProcessSerialNumber *')
    psn[0] = (0, kCurrentProcess)
    throw(lib.TransformProcessType(psn, kProcessTransformToForegroundApplication))

def isvalidpid(pid):
    try:
        os.kill(pid)
    except OSError:
        return False
    return True

def copyscriptingdefinition(path):
    fs_ref = FSRef(path)
    sdef = ffi.new('CFDataRef *')
    throw(lib.OSACopyScriptingDefinition(fs_ref, 0, sdef))
    data = ffi.buffer(lib.CFDataGetBytePtr(sdef[0]), lib.CFDataGetLength(sdef[0]))[:]
    lib.CFRelease(sdef[0])
    return data

if __name__ == '__main__':
    newlist()
    newrecord()
    print(stringsforosstatus(0))
    print(findapplicationforinfo(b'????', 'com.apple.TextEdit', None))
    print(launchapplication('/Applications/TextEdit.app'))
    print(psnforapplicationpath('/Applications/TextEdit.app'))
    print(copyscriptingdefinition('/Applications/TextEdit.app'))
    transformprocesstoforegroundapplication()

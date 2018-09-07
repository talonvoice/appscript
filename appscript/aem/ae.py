# CFFI implementation of the API surface provided by oldschool py-appscript's ae.c

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

from .ae_api import ffi
lib = ffi.dlopen('/System/Library/Frameworks/Carbon.framework/Carbon')

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
        if lib: # work around error in python2 on exit
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

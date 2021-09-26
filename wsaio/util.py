import base64
import hashlib
import os

WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


def genmask():
    return os.urandom(4)


def mask(data, mask):
    return bytes(data[i] ^ mask[i % 4] for i in range(len(data)))


def genseckey():
    return base64.b64encode(os.urandom(16)).decode()


def genacckey(key):
    return base64.b64encode(hashlib.sha1(key + WS_GUID).digest()).decode()


def getbytes(obj):
    if obj is None:
        return b''
    elif isinstance(obj, bytes):
        return obj
    elif isinstance(obj, str):
        return obj.encode('utf-8')
    elif isinstance(obj, memoryview):
        return obj.tobytes()
    elif isinstance(obj, bytearray):
        return bytes(obj)
    elif isinstance(obj, int):
        return obj.to_bytes(1, 'big')

    raise TypeError(f'Expected a str, int or bytes-like object, got {type(obj).__name__}')

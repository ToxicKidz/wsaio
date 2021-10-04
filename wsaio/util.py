import base64
import hashlib
import os

WS_GUID = b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11'


def genmask():
    """Generates a random masking key for a WebSocket frame."""
    return os.urandom(4)


def mask(data, mask):
    """Applies a masking key to a byte string.

    Arguments:
        data (bytes): The data to apply the masking key to.

        mask (bytes): The masking key.
    """
    return bytes(data[i] ^ mask[i % 4] for i in range(len(data)))


def genseckey():
    """Generates a random base64 value for a secret WebSocket key."""
    return base64.b64encode(os.urandom(16)).decode('utf-8')


def genacckey(key):
    """Generates the acceept key for a secret WebSocket key.

    Arguments:
        key (str): The secret WebSocket key.
    """
    return base64.b64encode(hashlib.sha1(key + WS_GUID).digest()).decode('utf-8')


def getbytes(obj):
    """Converts an object to bytes.

    - If the object is None an empty byte string is returned.
    - If the object is a byte string, it is returned.
    - If the object is a str, the value of `str.encode('utf-8')` is returned.
    - If the object is a memoryview, the value of `memoryview.tobytes()` is returned.
    - If the object is a bytearray, the value of `bytes(bytearray)` is returned.
    - If the object is an int, the value of `bytes([int])` is returned.

    Raises:
        TypeError: The object could not be converted to a byte.

        ValueError: The object is an integer that can not be represented with a single byte.
    """
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
        if 0 <= obj <= 255:
            return bytes((obj,))

        raise ValueError(f'{obj} can not be represented with a single byte')

    raise TypeError(f'Expected a str, int or bytes-like object, got {type(obj).__name__}')

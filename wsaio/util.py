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
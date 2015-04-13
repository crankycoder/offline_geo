import struct

def pack_24bits(v):
    values = []
    values.append((v>>16) & 0xff)
    values.append((v>>8) & 0xff)
    values.append(v & 0xff)
    return struct.pack("BBB", *values)

def unpack_24bits(v):
    values = struct.unpack("BBB", v)
    return (values[0] << 16) + (values[1] << 8) + (values[2])
import struct

def pack_24bits(v):
    values = []
    values.append((v>>16) & 0xff)
    values.append((v>>8) & 0xff)
    values.append(v & 0xff)
    return struct.pack("BBB", *values)

def unpack_24bits(v):
    values = struct.unpack("BBB", v)
    return (values[0] << 16) + (values[1] << 8) + (values[2])

"""Generate the app's simple four-tile mark without external image tools."""
from pathlib import Path
import struct
import zlib

root=Path(__file__).resolve().parents[1]/'client'
def chunk(kind,data):
    return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data)&0xffffffff)
for size in (192,512):
    pixels=bytearray()
    for y in range(size):
        pixels.append(0)
        for x in range(size):
            a,b=x/size,y/size
            square=((.24<a<.47 and .24<b<.47) or (.53<a<.76 and .24<b<.47) or (.24<a<.47 and .53<b<.76))
            circle=(a-.645)**2+(b-.645)**2 < .115**2
            pixels.extend((213,245,120) if square or circle else (20,40,33))
    png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',size,size,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(pixels))+chunk(b'IEND',b'')
    (root/f'icon-{size}.png').write_bytes(png)

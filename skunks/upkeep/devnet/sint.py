# sint.py N: the hex of an ErgoScript Int constant (type byte 04, zigzag VLQ), as a box register takes it.
import sys
n = int(sys.argv[1]); z = ((n << 1) ^ (n >> 31)) & 0xffffffff
out = []
while True:
    b = z & 0x7f; z >>= 7
    if z: out.append(b | 0x80)
    else: out.append(b); break
print("04" + "".join("%02x" % b for b in out))

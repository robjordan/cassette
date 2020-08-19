#! /usr/bin/env python
#
# cassette: Interpret an Exidy Sorceror 'cassette' in WAV file format
#
# Relevant details on the coding: http://tiny.cc/ltcnsz
# "At 300 baud a 0 is encoded as four cycles of a 1200Hz square wave and a 1 is
# eight cycles at 2400Hz. At 1200 baud a 0 is half a cycle at 600Hz and a 1 is
# one cycle at 1200Hz tone. Or, if you prefer, at 1200 baud the output level is
# always toggled once at the start of the bit, and if the bit is a 0 then it is
# toggled again halfway through.""

import sys
import wave
from scipy.io import wavfile
from scipy.signal import butter, lfilter
import numpy as np
import matplotlib.pyplot as plt
import argparse

# tuneable constants
silence = 5000
order = 6
lowcut = 200
hicut = 3000

# global data
blocks = []
num_blocks = 0


def find(condition):    # used to be in matplotlib
    res, = np.nonzero(np.ravel(condition))
    return res


def butter_bandpass(lowcut, highcut, fs, order=5):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return b, a


def butter_bandpass_filter(data, lowcut, highcut, fs, order=5):
    b, a = butter_bandpass(lowcut, highcut, fs, order=order)
    y = lfilter(b, a, data)
    return y


def get_tones(fname):
    w = wave.open(fname, 'rb')
    print("Filename:\t", fname)
    print("Channels:\t", w.getnchannels())
    print("Sample width:\t", w.getsampwidth())
    print("Frame rate:\t", w.getframerate())
    print("Frames:\t\t", w.getnframes())
    print("Compression:\t", w.getcomptype())
    if w.getcomptype() != 'NONE':
        exit("Compressed files are not supported.")
    if w.getnchannels() != 1:
        exit("Please convert file to mono.")

    # read complete audio data into numpy array
    samplerate, data = wavfile.read(fname)
    length = data.shape[0] / samplerate
    print("Duration:\t", round(length, 1), "seconds")

    # eliminate silent or near-silent header and trailer
    s = 0
    f = len(data)-1
    while (abs(data[s]) < silence):
        s += 1
    while (abs(data[f]) < silence):
        f -= 1
    data = data[s-1:f]

    # Bandpass filter to the range around 600Hz to 2400Hz
    # data = butter_bandpass_filter(data, lowcut, hicut, samplerate, order)

    # Find zero-crossings (both rising and falling edges)
    data = data.astype(np.int32)    # prevent maths overflows
    # Find index of point before crossing, then interpolate
    indices = find(
        (data[1:] >= 0) & (data[:-1] < 0) | (data[1:] < 0) & (data[:-1] >= 0)
        )
    cross = [i - data[i] / (data[i+1] - data[i]) for i in indices]

    # Calculate frequency based on the half-wavelength between zero-crossings
    freq = [samplerate/((cross[i]-cross[i-1])*2) for i in range(1, len(cross))]
    rounded = [int(round(f, -2)) for f in freq]
    counts = dict()
    for i in rounded:
        counts[i] = counts.get(i, 0) + 1
    print("Frequencies:\t", end='')
    for c in counts:
        print(" {} ({}%)".format(c, round(100*counts[c]/len(freq))), end='')
    print()
    baud = 0

    # Allow some leeway... hope that flaky files can still be read
    if (1200 in counts) | (1100 in counts) | (1300 in counts):
        if (600 in counts) | (500 in counts) | (700 in counts):
            print("Looks like 1200 baud.")
            baud = 1200
        elif (2400 in counts) | (2300 in counts) | (2500 in counts):
            print("Looks like 300 baud.")
            baud = 300
        else:
            exit("Looks faulty: 1200Hz only.")
    else:
        exit("Looks faulty: no 1200Hz tone.")

    # Assemble a string that contains H (2400), M (1200) or L (300) for every
    # half-wavelength of the file
    seq = ""
    for f in freq:
        if f > 1800:
            # 2400 Hz tone is always High
            seq += 'H'
        elif f > 900:
            # 1200 Hz tone...
            if baud == 300:
                # ... is Low at 300 baud ...
                seq += 'L'
            elif baud == 1200:
                # ... but is High at 1200 baud
                seq += 'H'
        elif f > 450:
            # 600 Hz tone is always Low
            seq += 'L'
        else:
            print("Unidentified tone, i: " + str(len(seq)) + " f: " + str(f))
            # Plot histogram to help with diagnosis
            plt.hist(freq, bins=100)
            plt.show()
            exit("Unidentified tone")

    return(baud, seq)


def get_bits(baud, seq):
    i = 0
    bits = ''

    # Start by skipping past all the High pilot tone
    while (seq[i] == "H") & (i < len(seq)):
        i += 1

    # Now we should be looking at a Low tone, the start of a 0 bit and the
    # start of the relevant bit stream. The frequency sequence depends on baud
    # rate, so let's take each case separately.
    if baud == 300:
        while i < len(seq):
            # Each letter in seq represents a half-cycle. A well-formed
            # sequence should have either:
            # "LLLLLLLL", which means 0, or
            # "HHHHHHHHHHHHHHHH", which means 1.
            if seq[i:i+8] == "LLLLLLLL":
                bits += "0"
                i += 8
            elif seq[i:i+16] == "HHHHHHHHHHHHHHHH":
                bits += "1"
                i += 16
            else:
                # Two cases:
                # 1. We've finished the valid data, just some closing 'H'
                # 2. The sequence is invalid.
                if ((len(seq) - i) < 16) & ("L" not in seq[i:]):
                    # All good, finish the loop and return
                    break
                else:
                    print("Invalid sequence, i, seq:", i, seq[i:i+16])
                    print("Read: ", i, " Total: ", len(seq))
                    print("Bits so far: ", bits)
                    exit("Invalid sequence")
    elif baud == 1200:
        while i < len(seq):
            # Each letter in seq represents a half-cycle. A well-formed
            # sequence should have either:
            # "L", which means 0, or
            # "HH", which means 1.
            if seq[i:i+1] == "L":
                bits += "0"
                i += 1
            elif seq[i:i+2] == "HH":
                bits += "1"
                i += 2
            else:
                # Two cases:
                # 1. We've finished the valid data, just some closing 'H'
                # 2. The sequence is invalid.
                if ((len(seq) - i) < 2) & ("L" not in seq[i:]):
                    # All good, finish the loop and return
                    break
                else:
                    print("Invalid sequence, i, seq:", i, seq[i:i+2])
                    exit("Invalid sequence")
    return bits


def get_bytes(bits):
    # Each 8-bit byte is transmitted as:
    # 1 start bit (always 0)
    # 8 data bits, LSB first
    # 2 stop/parity bits (always 0b11)
    b = bytearray()
    i = 0
    while (i <= len(bits)-11):  # if there's one complete 11-byte sequence left
        # extract bits 2-9 of 11, and reverse them
        b.append(np.uint8(int(bits[i+1:i+9][::-1], 2)))
        i += 11
    return b


def crc_block(bytes):  # extract the requisite bytes and compute CRC
    crc = np.uint8(0)
    save = np.seterr(all='ignore')  # ignore byte overflow
    for byte in bytes:
        byte = np.uint8(byte)  # weirdly, iterating a bytearray returns an int
        # it might overflow, but that's ok
        crc = byte - crc
        crc = ~crc
    np.seterr(**save)  # restore saved error settings
    return crc


def reverse_bytes(bytes):
    return hex((np.uint8(bytes[1]) << 8) | np.uint8(bytes[0]))


def print_header(bytes):
    # Header layout in this document: https://tinyurl.com/y2tzqqfs
    # "Exidy Sorcerer Software Internals Manual 1979"
    print("Name:\t\t", "".join(map(chr, bytes[0:5])))
    print("Header ID:\t", hex(bytes[5]))
    print("Filetype:\t", hex(bytes[6]), "Basic" if bytes[6] == 0xC2 else "")
    length = reverse_bytes(bytes[7:9])
    print("Length:\t\t", length)
    print("Load address:\t", reverse_bytes(bytes[9:11]))
    print("Go address:\t", reverse_bytes(bytes[11:13]))
    return int(length, 0)


def load_block(bytes, crc):
    global num_blocks
    global blocks

    actual_crc = crc_block(bytes)
    print("Block: {}: Length: {} CRC: 0x{:02x} {}".format(
        num_blocks,
        len(bytes),
        actual_crc,
        "OK" if actual_crc == crc else "ERROR"
    ))
    blocks.append((bytes, len(bytes)))
    num_blocks += 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'wavfile',
        help='input: a WAV recording of a Sorceror program')
    parser.add_argument(
        '-o',
        '--output',
        help="file to which binary representation will be written",
        action='store')
    args = vars(parser.parse_args())

    # find edges in audio data, infer baud rate and return a sequence of tones
    baud, seq = get_tones(args['wavfile'])

    # convert tones to bits according to protocol in tech ref
    bits = get_bits(baud, seq)

    # eliminate start/stop bits, invert MSB/LSB
    bytes = get_bytes(bits)

    # decode header block and fine length of data in recording
    length = print_header(bytes[101:117])
    load_block(bytes[101:117], bytes[117])

    # load data blocks
    n = 0
    while length > 0:
        load_block(
            bytes[219+n*257:219+n*257+min(256, length)],
            bytes[219+n*257+min(256, length)])
        n += 1
        length -= min(256, length)

    # save data as a binary file: 16 bytes header, then pure data
    if args['output']:
        try:
            of = open(args['output'], "wb")
            for b in range(0, num_blocks-1):
                of.write(blocks[b][0])
        except Exception as e:
            exit(e)

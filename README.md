# Cassette: Load Exidy Sorcerer software from a WAV file, as if from Cassette

[Exidy Sorcerer](https://en.wikipedia.org/wiki/Exidy_Sorcerer) loaded software from Cassette tapes using a protocol based on dual tones, representing 0 or 1 bits, which could operate at either 300 or 1200 baud. This audio-based interface was low (especially at 300 baud) and unreliable (especially at 1200 baud).

Enthusiasts have developed alternative ways to load software e.g. emulators, or peripherals using a digital interface. To use such a method, we'd need the software to be in a binary format, rather than the audio format typically recovered from the cassettes of the period.

The aim of this quickly-developed utility is to convert a WAV file containing a recording of a Sorcerer cassette into a binary format.

It works for many, but not all, of the WAV files found in Terry Smith's [amazing trove of Sorcerer software](https://www.classic-computers.org.nz/blog/2017-01-23-software-for-real-sorcerers.htm). Irony alert: Many of Tezza's WAV files were sourced by loading binary files into the [MESS emulator](https://www.mess.org/) and saving as WAV. I wasn't aware of the BIN format used by MESS when I started this utility.

The coding scheme that coverts bits to tones and vice versa is documented in the [Sorcerer Technical Manual](https://ia800709.us.archive.org/28/items/Sorcer_Technical_Manual_1979-03_Exidy/Sorcer_Technical_Manual_1979-03_Exidy.pdf). At 300 baud a 0 is encoded as four cycles of a 1200Hz square wave and a 1 is eight cycles at 2400Hz. At 1200 baud a 0 is half a cycle at 600Hz and a 1 is one cycle at 1200Hz tone.  

The BIN format I use is based on the 'file' format used by Sorcerer to save to tape. It's documented in the [Sorceror Software Internals Manual](https://archive.org/details/Exidy_Software_Internals_Manual_1979_Tolomei_Vic). 

A 16-byte header is read from the tape, and written to the first 16 bytes of the BIN file. The header block is followed by a CRC check byte, which this utility checks then discards. In the actual Sorceror, these 16-bytes are loaded into the Monitor Work Area (MWA) and are structured like this:

(https://github.com/robjordan/cassette/raw/master/mwa.png)"16-byte header".

Note that the header specifies the number of bytes of actual content in the 'file', ie excluding header, CRC, etc. 

The tape then contains a series of 256-byte blocks, each one followed by a CRC byte, and finally a partial block when there are fewer than 256 bytes remaining of the data as specified by the length stated in the header. This utility reads each block in turn, checks then discards the CRC, and then saves 256 bytes (or fewer in the final block) to the BIN file.

Thus the resulting BIN file comprises a 16-byte header followed by pure Z80 binary code. 

Additional notes:
- It's very lightly tested at present, and hasn't been exposed to a variety of real WAV files. Tezza's files are quite ideal as they are digitally reconstructed by saving from the MESS emulator.
- I briefly attempted to apply a bandpass filter to limit the audio to 300-3700 Hz, as per the Sorcerer hardware. I think the filter acts correctly but it didn't improve demodulation at all (in fact it got worse), so it's commented out. Something to play with later.
- There is an alternative tool that fulfills the same purpose, but supports a much wider range of systems and functionality, but it didn't immediately work from me (I run Linux and the tool requires .NET, therefore Mono emulating .NET on Linux). It's [tapetool2](https://www.toptensoftware.com/tapetool/) by Brad Robinson.
- I don't yet have any hardware which can load and run these binary files. I'm hoping to build something like [ClausB's amazing Teensy tape simulator](http://www.vcfed.org/forum/showthread.php?49163-Exidy-Sorcerer-II-Questions&p=545053#post545053).

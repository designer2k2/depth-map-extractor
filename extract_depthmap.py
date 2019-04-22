#!/usr/bin/python3
#encoding=utf-8

# Extracts the unaltered image, and the depth map from a image taken with the bokeh mode on a Huawei phone.
# The files can be posted directly on Facebook to generate a 3D Image.

# Extended to work with P10, P20, P30, Mate20 Phones and Facebook by Stephan Martin 
# based on the script from João Paulo Barraca for the P9

import sys
import os
import binascii
from PIL import Image
import PIL.ImageOps 

def extract_edof(data, idx, fname):
		
	if  data.find(bytes([0x00, 0x65, 0x64, 0x6f, 0x66, 0x00])) > 0:
		edofpos = data.find(bytes([0x00, 0x65, 0x64, 0x6f, 0x66, 0x00]))
		print("\t* found EDOF at %d, should be: %d,offset %d" % (edofpos,idx,edofpos-idx))
		idx = edofpos - 3
	
	if data[idx + 4:idx + 8] != b'edof':
		print("ERROR: Frame is not EDOF")
		return False
	
	idx += 8
	columns = int.from_bytes(data[idx + 16: idx + 18], byteorder='little')
	rows = int.from_bytes(data[idx + 18: idx + 20], byteorder='little')
	print("\t* found EDOF at %d with geometry=%dx%d" % (idx, columns, rows))

	orientation = data[idx + 7]

	idx += 68
	img = Image.frombuffer('L', (columns, rows), data[idx:], 'raw', 'L', 0, 0)
	img = PIL.ImageOps.invert(img)
	if orientation == 0x10:
		img = img.transpose(Image.FLIP_TOP_BOTTOM)
	elif orientation == 0x12:
		img = img.transpose(Image.FLIP_LEFT_RIGHT)
	elif orientation == 0x13:
		img = img.transpose(Image.TRANSPOSE)

	outfname = (''.join(fname.split('.')[:-1])) + '-1_depth.png'
	print("\t  * saving depth map to %s" % outfname)
	img.save(outfname)

	return True


def scan_segment(data, idx, fname, segment_index):
		
	#this looks ahead to the correct position, there is something between the segments.
	if  data.find(bytes([0xff, 0xd8]),idx) > 0:
		startpos = data.find(bytes([0xff, 0xd8]),idx)
		error = startpos - idx
		print("\t* found startpos at %d, should be: %d,error %d" % (startpos,idx,error))
		if error < 15000:
			idx = startpos 	#only correct small errors! P10/20 mate20 = 1208, p30 = 11692
		else:
			print("\t* Error larger than 15000, skippind")
	
	
	if data[idx:idx + 2] != b'\xff\xd8':
		print("\t* wrong segment %d, range %d" % (segment_index, idx))
		return -1
		
	i = idx + 2
	while i < len(data):
		if data[i] == 0xff:
				if data[i + 1] == 0xd9 or data[i + 1] == 0xd8:
					i += 2
					continue

				if data[i + 1] == 0xda:
					j = i + 2
					while not (data[j] == 0xff and data[j + 1] == 0xd9):
						j += 1
					
					j += 1

					print("\t* found segment %d, range %d to %d, length %d" % (segment_index, idx, j, j - idx))

					if segment_index == 1:
						outfname = (''.join(fname.split('.')[:-1])) + ('-%d.JPG' % segment_index)
						print("\t * saving segment to %s" % outfname)
						f = open(outfname, "wb")
						f.write(data[idx: j + 1])
						f.close()

					return j 
				
				length = 256 * data[i+2] + data[i+3] + 2
				i += length

				continue
		i += 1

	return 0

def print_usage():
	print("Usage: img1 img2 img3... ")
	print("Handling: ")
	print("Extracts the unalterd image and depth map image.")


def main(fname):
	print("Processing: %s" % fname)
	fin = None

	try:
		fin = open(fname, "rb")
	except FileNotFoundError:
		print("ERROR: Could not open %s" % fname)
		return False

	data = fin.read()

	if data[:3] != b'\xff\xd8\xff':
		print("No JPEG header found")
		return False

	print ("\t* scanning file")

	if  data.find(bytes([0x00, 0x65, 0x64, 0x6f, 0x66, 0x00])) < 0:
		print("No EDOF header found, use a bokeh mode image")
		return False

	idx = 0
	segment_index = 0
	while True:
		r = scan_segment(data, idx, fname, segment_index)
		if r == -1:
			if segment_index > 1:
				return extract_edof(data, idx, fname)
			else:
				return False

		segment_index += 1
		idx = r + 1

		if idx > len(data):
			return False
		

if __name__ == "__main__":
	print("Huawei Camera EDOF Extractor\n")

	if sys.version_info[0] < 3:
		print("This script requires Python 3")
		sys.exit(-1)

	if len(sys.argv) < 2:
		print_usage()
		sys.exit(-1)
	else:
				
		for p in sys.argv[1:]:
			if p[0] != "-":
				if not os.path.exists(p):
					print("File not found: %s" % p)
					continue

				r = main(p)

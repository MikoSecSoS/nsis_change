import os
import struct
import argparse
from zlib import crc32

parser = argparse.ArgumentParser(description="Replace nsis exe file")
parser.add_argument("-f", "--file", required=True, help="source nsis exe")
parser.add_argument("-o", "--output", help="replace app output file name")
parser.add_argument("-x", dest="extract", help="extract app file name")
parser.add_argument("--app", help="repalce app.7z")

args = parser.parse_args()

def read_file(filename, mode="rb"):
	with open(filename, mode) as f:
		data = f.read()
	return data

def save_file(filename, data, mode="wb"):
	with open(filename, mode) as f:
		f.write(data)

class NsisParser(object):
	def __init__(self, filename):
		self.filename = filename
		with open(self.filename, "rb") as f:
			self.nsis_file_data = f.read()

	def parse_nsis(self):
		# 总大小
		self.nsis_file_size = len(self.nsis_file_data)
		
		# Nsis数据偏移
		self.nsis_data_offset    = self.nsis_file_data.find(b"\x00\x00\x00\x00\xEF\xBE\xAD\xDE\x4E\x75\x6C\x6C\x73\x6F\x66\x74\x49\x6E\x73\x74")
		
		# 读取Nsis数据头中的Nsis数据整体大小。 头部加24字节，4字节是NSIS数据（包含CRC32数据）大小
		self.nsis_data_size      = struct.unpack("<I", self.nsis_file_data[self.nsis_data_offset+24:self.nsis_data_offset+24+4])[0]
		# 总大小 - NSIS数据偏移 = NSIS数据大小
		self.nsis_data_calc_size = self.nsis_file_size - self.nsis_data_offset
		
		# Nsis数据
		self.nsis_data           = self.nsis_file_data[self.nsis_data_offset:self.nsis_data_offset+self.nsis_data_size] # 后4字节是CRC32数据
		
		# Nsis中的7z数据
		self.nsis_7zAPP_offset   = self.nsis_data.find(b"\x37\x7A\xBC\xAF\x27\x1C")
		nsis_7z_NextHeaderOffset = struct.unpack("<Q", self.nsis_data[self.nsis_7zAPP_offset+0xC:self.nsis_7zAPP_offset+0xC+8])[0]
		nsis_7z_NextHeaderSize   = struct.unpack("<Q", self.nsis_data[self.nsis_7zAPP_offset+0x14:self.nsis_7zAPP_offset+0x14+8])[0]
		self.nsis_7zAPP_size     = nsis_7z_NextHeaderOffset+nsis_7z_NextHeaderSize+0x1F+1
		self.nsis_7zAPP_data     = self.nsis_data[self.nsis_7zAPP_offset:self.nsis_7zAPP_offset+self.nsis_7zAPP_size]
		
		# Nsis数据中的CRC32值
		self.nsis_data_crc32     = struct.unpack("<I", self.nsis_file_data[-4:])[0]
		self.nsis_data_crc32_big = struct.unpack(">I", struct.pack("<I", self.nsis_data_crc32))[0] # self.nsis_file_data[-4:]
		
		# Nsis计算出的CRC32值
		self.nsis_calc_data      = self.nsis_file_data[0x200:-4]
		self.nsis_calc_data_size = len(self.nsis_calc_data)
		self.nsis_calc_crc32     = crc32(self.nsis_calc_data)
		self.nsis_calc_crc32_big = struct.unpack(">I", struct.pack("<I", self.nsis_calc_crc32))[0] # struct.pack("<I", crc32(self.nsis_calc_data))

	def replace_app(self, app_data):
		new_nsis_7zAPP_size = len(app_data)

		pad_num = 0
		if new_nsis_7zAPP_size < self.nsis_7zAPP_size:
			isPad = input("新的app文件小于原始app文件，是否补0保证exe大小不变?[Y/n]")
			if isPad.lower() != "n":
				pad_num = self.nsis_7zAPP_size - new_nsis_7zAPP_size

		# 计算新的Nsis数据大小
		new_nsis_data_size = self.nsis_data_calc_size - self.nsis_7zAPP_size + new_nsis_7zAPP_size + pad_num

		# 替换新的app和新的Nsis数据大小和新的7z压缩包大小，但是没crc32计算后的值
		start_data = self.nsis_file_data[:self.nsis_data_offset+self.nsis_7zAPP_offset]
		start_data = start_data[:self.nsis_data_offset+24] + struct.pack("<I", new_nsis_data_size) + start_data[self.nsis_data_offset+24+4:]
		start_data = start_data[:-4] + struct.pack("<I", new_nsis_7zAPP_size) # -4是app-32/64.7z压缩包的大小4字节。
		end_data = self.nsis_file_data[self.nsis_data_offset+self.nsis_7zAPP_offset+self.nsis_7zAPP_size:-4]
		nsis_file_data_nocrc32 = start_data + app_data + (b'\x00' * pad_num) + end_data

		# Nsis计算出的CRC32值
		crc32_value = crc32(nsis_file_data_nocrc32[0x200:])
		crc32_big = struct.pack("<I", crc32_value)

		print("----Replace APP----")
		print(f"New APP 7zAPP Name    : {args.app}")
		print(f"Source APP 7zAPP Size : 0x{self.nsis_7zAPP_size:X}")
		print(f"New APP 7zAPP Size    : 0x{new_nsis_7zAPP_size:X}")
		print(f"Source Nsis Data Size : 0x{self.nsis_data_size:X}")
		print(f"New Nsis Data Size    : 0x{new_nsis_data_size:X}")
		print(f"Source CRC32 Value    : 0x{self.nsis_calc_crc32:X}")
		print(f"New CRC32 Value       : 0x{crc32_value:X}")
		print(f"Zero Pad num          : {pad_num}")
		print()

		# 替换完新的app并且拼接上新的crc32
		self.nsis_file_data = nsis_file_data_nocrc32 + crc32_big

		# 重新解析新的nsis信息
		self.parse_nsis()

	def show_info(self):
		print("========== Basic Info ==========")
		print(f"Nsis File Name       : {self.filename}")
		print(f"Nsis File Size       : 0x{self.nsis_file_size:X}")
		print(f"Nsis Data Offset     : 0x{self.nsis_data_offset:X}")
		print(f"Nsis Data Size       : 0x{self.nsis_data_size:X}")
		print(f"Nsis Data Calc Size  : 0x{self.nsis_data_calc_size:X}")
		print(f"Nsis 7zData Offset   : 0x{self.nsis_7zAPP_offset:X}")
		print(f"Nsis 7zData Size     : 0x{self.nsis_7zAPP_size:X}")
		print(f"Nsis Data CRC32      : 0x{self.nsis_data_crc32:X}")
		print(f"Nsis Data CRC32(Big) : 0x{self.nsis_data_crc32_big:X}")
		print(f"Nsis Calc CRC32      : 0x{self.nsis_calc_crc32:X}")
		print(f"Nsis Calc CRC32(Big) : 0x{self.nsis_calc_crc32_big:X}")
		print(f"Nsis CRC32 Data Size : 0x{self.nsis_calc_data_size:X}")
		print()

def main():
	nsisParser = None
	if args.file:
		if not os.path.exists(args.file):
			print(f"[*] path {args.file} not found.")
			return
		nsisParser = NsisParser(args.file)
		data = read_file(args.file)
		nsisParser.parse_nsis()
		nsisParser.show_info()

	if not nsisParser:
		return

	if args.extract:
		print(f"[*] Write to file -> {args.extract}")
		save_file(args.extract, nsisParser.nsis_7zAPP_data)

	if args.app:
		app_data = read_file(args.app)
		nsisParser.replace_app(app_data)
		nsisParser.show_info()

	if args.output:
		print(f"[*] Write to file -> {args.output}")
		save_file(args.output, nsisParser.nsis_file_data)

if __name__ == "__main__":
	main()
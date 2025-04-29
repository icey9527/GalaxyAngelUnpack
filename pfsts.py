import os
import sys
import json

import ctypes
import struct
from typing import Tuple, List

XOR_KEY = 0x72
BUFFER_SIZE = 16 * 1024 * 1024  # 16MB buffer
WINDOW_SIZE = 4096
MAX_MATCH_LEN = 18
MIN_MATCH_LEN = 3

class SlidingWindow:
    def __init__(self):
        self.data = bytearray(WINDOW_SIZE)
        self.pos = 0xFEE
        self.size = 0

def window_init(window: SlidingWindow) -> None:
    for i in range(WINDOW_SIZE):
        window.data[i] = 0
    window.pos = 0xFEE
    window.size = 0

def window_update(window: SlidingWindow, byte: int) -> None:
    window.data[window.pos] = byte
    window.pos = (window.pos + 1) % WINDOW_SIZE
    if window.size < WINDOW_SIZE:
        window.size += 1

def find_match(window: SlidingWindow, input_data: bytearray, cursor: int, end: int) -> Tuple[int, int]:
    max_len = 0
    max_pos = 0
    search_start = (cursor - (WINDOW_SIZE - 8)) if (cursor >= (WINDOW_SIZE - 8)) else 0
    
    for i in range(search_start, cursor):
        length = 0
        while (length < MAX_MATCH_LEN and 
               i + length < cursor and 
               cursor + length < end and 
               input_data[i + length] == input_data[cursor + length]):
            length += 1
        
        if length > max_len:
            max_len = length
            max_pos = i
    
    distance = (window.pos - (cursor - max_pos)) % WINDOW_SIZE
    return (max_len, distance) if max_len >= MIN_MATCH_LEN else (0, 0)

def compress(input_data: bytearray) -> Tuple[bytearray, int]:
    input_size = len(input_data)

    if input_data[:4] == b'\x20\x33\x3B\x31' or input_data[:4] == b'\x20\x33\x3B\x30':
        
        return input_data, int.from_bytes(input_data[4:8], 'little'), input_size
    
    
    # Estimate max output size (input_size * 1.5 + 8)
    max_output_size = input_size + (input_size // 2) + 8
    output = bytearray(max_output_size)
    
    # Write header magic and original size
    output[0:4] = b'\x20\x33\x3B\x31'
    output[4:8] = struct.pack('<I', input_size)
    
    window = SlidingWindow()
    window_init(window)
    
    read_pos = 0
    output_pos = 8
    control_mask = 0
    control_bit = 0
    data_buffer = bytearray()
    
    while read_pos < input_size:
        match_len, distance = 0, 0
        if window.size >= MIN_MATCH_LEN:
            match_len, distance = find_match(window, input_data, read_pos, input_size)
        
        if match_len >= MIN_MATCH_LEN:
            control_mask |= (0 << control_bit)
            
            byte1 = distance & 0xFF
            byte2 = ((distance >> 4) & 0xF0) | ((match_len - 3) & 0x0F)
            
            data_buffer.append(byte1 ^ XOR_KEY)
            data_buffer.append(byte2 ^ XOR_KEY)
            
            for i in range(match_len):
                window_update(window, input_data[read_pos + i])
            read_pos += match_len
        else:
            control_mask |= (1 << control_bit)
            
            value = input_data[read_pos]
            data_buffer.append(value ^ XOR_KEY)
            
            window_update(window, value)
            read_pos += 1
        
        control_bit += 1
        
        if control_bit >= 8:
            ctrl_byte = control_mask ^ XOR_KEY
            output[output_pos] = ctrl_byte
            output_pos += 1
            
            output[output_pos:output_pos+len(data_buffer)] = data_buffer
            output_pos += len(data_buffer)
            
            control_mask = 0
            control_bit = 0
            data_buffer = bytearray()
    
    if control_bit != 0:
        while control_bit < 8:
            control_mask |= (0 << control_bit)
            control_bit += 1
        
        ctrl_byte = control_mask ^ XOR_KEY
        output[output_pos] = ctrl_byte
        output_pos += 1
        
        output[output_pos:output_pos+len(data_buffer)] = data_buffer
        output_pos += len(data_buffer)
    
    # Trim the output buffer to actual size
    
    return output, input_size, output_pos


def read_int(f, address=None):
    if address is None:
        return int.from_bytes(f.read(4), 'little')
    else:
        return int.from_bytes(f[address:address+4], 'little')

def write_int(file, content, address=None):
    if address is None:
        return
    else:
        cmd =  content.to_bytes(4, 'little')
        file[address:address+len(cmd)] = cmd
        return 
    
def packfsts(dir, list):
    data = bytearray(0x20 + len(list) * 4 * 4)
    data[0:4] = b"FSTS"
    write_int(data,len(list),0x4)
    write_int(data,0x20,0x8)
    str_start = len(data)
    write_int(data,str_start,0xC)
    
    
    addr = 16
    for filename, Ofilename in list:
        addr += 16
        write_int(data,len(data) - str_start,addr)
        data.extend(Ofilename.encode()+b'\x00')
    write_int(data,len(data)-str_start,0x10)
    data = data + b'\x00' * ((16 - (len(data) % 16)) % 16)
    
    addr = 16
    for filename, Ofilename in list:
        addr += 16
        print(os.path.join(dir,filename))
        compress_data, UncompressSize, size = compress(open(os.path.join(dir,filename), 'rb').read())
        write_int(data,len(data),addr + 4)
        write_int(data,UncompressSize,addr + 8)
        write_int(data,size,addr + 12)
        data = (data + compress_data) + b'\x00' * ((16 - (len(data + compress_data) % 16)) % 16)


    return data


def pack(input_dir, packname):
    try:
        with open(input_dir + '/list.json', 'r', encoding='utf-8') as file:
            list = json.load(file)
    except FileNotFoundError:
        print(f"文件未找到: {input_dir}/list.json")
        return
    except json.JSONDecodeError:
        print(f"文件不是有效的 JSON 格式: {input_dir}/list.json")
        return
    except Exception as e:
        print(f"读取文件时发生错误: {e}")
        return
    data = bytearray()
    data[0:] = bytes.fromhex(list['start'])
    del list['start']
    IdxQ = len(list)
    data.extend((IdxQ * 4  + 4 + IdxQ * 5 * 4) * b'\x00')
    
    #data[read_int(data, 0x18):] = b'\x00' * 6 * 4 * IdxQ
    idx_start = read_int(data, 0xC)
    write_int(data, IdxQ, 0x50)
    str_start = len(data)
    write_int(data, str_start, 0x20)
    data.extend(packname.encode()+b'\x00')

    addr = 0
    for key, value in list.items():
        print(key)
        if isinstance(value, dict):
            idx_addr = 0x54 + 4  * addr
            idx_addr2 =  0x54 + 4  * IdxQ + 4 * addr * 5
            write_int(data,len(data) - str_start, idx_addr2)
            write_int(data, idx_addr2 - 0x50, idx_addr)
            data.extend(key.encode()+b'\x00')
            addr += 1
    write_int(data,len(data)-str_start,0x24)
    data = data + b'\x00' * ((16 - (len(data) % 16)) % 16)

    addr = 0
    for key, value in list.items():
        if isinstance(value, dict):
            data += b'\x00' * ((2048 - (len(data) % 2048)) % 2048)
            idx_addr = 0x54 + 4  * addr
            idx_addr2 =  0x54 + 4  * IdxQ + 4 * addr * 5
            write_int(data, len(data), idx_addr2 + 8)
            fsts_data = packfsts(os.path.join(input_dir,key), value.items())
            fsts_data = fsts_data + b'\x00' * ((16 - (len(fsts_data) % 16)) % 16)
            write_int(data, len(fsts_data), idx_addr2 + 12)
            write_int(data, len(value), idx_addr2 + 16)
            data.extend(fsts_data)
            
            addr += 1

    with open(packname, 'wb') as f:
        f.write(data)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法：\n封包：打包目录 封包文件")
    else:
        pack(sys.argv[1],sys.argv[2])

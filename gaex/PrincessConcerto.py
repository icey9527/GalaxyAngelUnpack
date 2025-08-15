import struct
import os
import sys

def hex_print(*args, **kwargs):
    hex_args = [f"0x{int(x):X}" if isinstance(x, (int, float)) else str(x) for x in args]
    print(*hex_args, **kwargs)

def function_453660(data):
    result = 0x23456789
    length = len(data)
    if length == 0:
        return result
    for i in range(length):
        current_char = data[i]
        v3 = result + current_char
        shift = (v3 + i) % 32
        rotated = ((v3 << shift) | (v3 >> (32 - shift))) & 0xFFFFFFFF
        result = (result + rotated) & 0xFFFFFFFF
    return result

def list_file(data):
    offset = 0
    result = {}

    while offset + 12 <= len(data):
        name_length, = struct.unpack_from('<I', data, offset)
        offset += 8
        address = struct.unpack_from('<I', data, offset)
        offset += 4

        name_bytes_length = name_length
        if offset + name_bytes_length > len(data):
            break

        file_name = data[offset:offset + name_bytes_length].decode('cp932')
        offset += name_bytes_length + 1

        result[str(address[0])] = file_name


    return result



def decompress(data: bytes, output_size: int) -> bytes:
    output = bytearray()
    ring_buffer = bytearray(4096)  # 环形缓冲区
    uVar8 = 0xFEE  # 初始环形缓冲区位置4078
    uVar6 = 0       # 位缓冲区
    pos = 0         # 当前处理的数据位置

    while len(output) < output_size:
        # 处理字面量或匹配对
        while True:
            uVar6 = (uVar6 >> 1) & 0xFFFF  # 右移一位并保持16位
            if (uVar6 & 0x100) == 0:       # 检查是否需要补充位
                if pos >= len(data):
                    raise ValueError("数据不足，无法继续解压")
                b = data[pos]
                pos += 1
                uVar6 = (b | 0xFF00) & 0xFFFF  # 更新位缓冲区
            if (uVar6 & 1) == 0:          # 当前位为0，处理匹配对
                break
            # 处理字面量
            if pos >= len(data):
                raise ValueError("数据不足，无法读取字面量")
            literal = data[pos]
            pos += 1
            output.append(literal)
            ring_buffer[uVar8] = literal
            uVar8 = (uVar8 + 1) & 0xFFF    # 更新环形缓冲区位置
            if len(output) == output_size:
                return bytes(output)

        # 处理匹配对
        if pos + 1 >= len(data):
            raise ValueError("数据不足，无法读取匹配对信息")
        bVar1 = data[pos]
        bVar2 = data[pos + 1]
        pos += 2
        offset = ((bVar2 & 0xF0) << 4) | bVar1  # 计算偏移量
        offset &= 0xFFF                          # 确保12位
        length = (bVar2 & 0x0F) + 3              # 计算长度

        # 复制匹配数据
        for i in range(length):
            src_pos = (offset + i) % 4096        # 源位置
            value = ring_buffer[src_pos]
            output.append(value)
            ring_buffer[uVar8] = value           # 更新环形缓冲区
            uVar8 = (uVar8 + 1) & 0xFFF
            if len(output) == output_size:
                return bytes(output)
    
    return bytes(output)



def decrypt_data_from_checksum(data: bytes, checksum_value: int) -> bytes:

    byte0 = checksum_value & 0xFF
    byte1 = (checksum_value >> 8) & 0xFF
    byte2 = (checksum_value >> 16) & 0xFF
    byte3 = (checksum_value >> 24) & 0xFF

    v3_unsigned = (byte3 + byte2 + byte1 + byte0) & 0xFF

    xor_key_byte = 0xAA if v3_unsigned == 0 else v3_unsigned

    decrypted_data = bytearray(len(data))
    for i in range(len(data)):
        decrypted_data[i] = data[i] ^ xor_key_byte

    return bytes(decrypted_data)




def parse_packed_file(input_file, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    
    with open(input_file, 'rb') as f:
        current_offset = 0
        index = 0

        list_filename = None
        
        while True:
            f.seek(current_offset)
            header = f.read(12)
            if len(header) < 12:
                break
            
            uncompressed = struct.unpack('<I', header[0:4])[0] ^ 0x1f84c9af
            compressed = struct.unpack('<I', header[4:8])[0] ^ 0x9ed835ab
            checksum = struct.unpack('<I', header[8:12])[0]

            #print(f'{hex(current_offset)} {index} {hex(uncompressed)} {hex(compressed)} {hex(checksum)}')
            
            if compressed != 0:
                x = decrypt_data_from_checksum(f.read(compressed), checksum)
                data = decompress(x, uncompressed)
                #hex_print(checksum, function_453660(x))
                
                
            else:
                data = f.read(uncompressed)


            if list_filename:
                key = str(current_offset - idx_size)
                output_path = os.path.join(output_dir, list_filename.get(key, key))
                outdir, name = os.path.split(output_path)
                print(name)
                os.makedirs(outdir, exist_ok=True)
                with open(output_path, 'wb') as out:
                    out.write(data)
            
            if index == 0:
                list_filename = list_file(data)
                idx_size = compressed + 12
                with open(os.path.join(output_dir, 'namelist'), 'wb') as out:
                    out.write(data)

            index += 1
            current_offset += 12 + (compressed if compressed != 0 else uncompressed)
        

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 3:
        print("Usage: python unpack.py <input_file> <output_dir>")
        sys.exit(1)
    
    parse_packed_file(sys.argv[1], sys.argv[2])
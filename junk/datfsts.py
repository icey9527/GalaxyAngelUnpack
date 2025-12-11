import os
import sys
import json
from io import BytesIO

def read_int(f, address=None):
    if address is not None:
        f.seek(address)
    return int.from_bytes(f.read(4), 'little')

def read_string(f, offset):
    f.seek(offset)
    string_bytes = bytearray()
    while True:
        char = f.read(1)
        if char == b'\x00' or not char:
            break
        string_bytes.extend(char)
    try:
        return string_bytes.decode('shift-jis')  # 尝试日文编码
    except UnicodeDecodeError:
        return string_bytes.decode('latin1')  # 回退到latin1编码

def uncompress(data, output_dir, filename):
    param_2 = int.from_bytes(data[4:8], 'little')
    param_4 = len(data)
    iVar4 = 8
    iVar11 = 0
    uVar7 = 0xfee
    uVar10 = 0
    abStack_1020 = bytearray(0x1020)
    uncompress_data = bytearray()

    compstate = False
    if len(data) > 3 and (data[1] == ord('3') and data[2] == ord(';') and data[3] == ord('1')):
        while True:
            while True:
                uVar10 >>= 1
                uVar6 = uVar10
                if (uVar10 & 0x100) == 0:
                    if param_4 <= iVar4:
                        return write_output(output_dir, filename, uncompress_data)
                    pbVar8 = data[iVar4]
                    iVar4 += 1
                    uVar10 = (pbVar8 ^ 0x72) | 0xff00
                    uVar6 = pbVar8 ^ 0x72

                if (uVar6 & 1) != 0:
                    break

                if param_4 <= iVar4 + 1:
                    return write_output(output_dir, filename, uncompress_data)

                iVar9 = iVar4 + 1
                bVar1 = data[iVar4]
                iVar4 += 2
                bVar2 = data[iVar9]
                iVar9 = 0

                while iVar9 <= ((bVar2 ^ 0x72) & 0xf) + 2:
                    uVar6 = (bVar1 ^ 0x72 | ((bVar2 ^ 0x72) & 0xf0) << 4) + iVar9
                    iVar9 += 1
                    bVar3 = abStack_1020[uVar6 & 0xfff]
                    if iVar11 >= param_2:
                        break
                    uncompress_data.append(bVar3)
                    abStack_1020[uVar7] = bVar3
                    uVar7 = (uVar7 + 1) & 0xfff
                    iVar11 += 1

            if param_4 <= iVar4:
                break
            bVar1 = data[iVar4]
            iVar4 += 1
            uncompress_byte = bVar1 ^ 0x72
            if iVar11 >= param_2:
                break
            uncompress_data.append(uncompress_byte)
            abStack_1020[uVar7] = uncompress_byte
            uVar7 = (uVar7 + 1) & 0xfff
            iVar11 += 1
    elif len(data) > 3 and (data[1] == ord('3') and data[2] == ord(';') and data[3] == ord('0')):
        if 8 < param_4:
            for i in range(8, param_4):
                uncompress_byte = data[i] ^ 0x72
                if iVar11 >= param_2:
                    break
                uncompress_data.append(uncompress_byte)
                iVar11 += 1
    else:
        return False

    return write_output(output_dir, filename, uncompress_data)

def write_output(output_dir, filename, data):
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)
    with open(output_path, 'wb') as f:
        f.write(data)
    return True

def process_fsts(fst_data, output_dir):
    f = BytesIO(fst_data)
    magic = f.read(4)
    if magic.decode('ascii') != 'FSTS':
        print("无效的FSTS文件头")
        return

    entries = []
    rebuild = {}
    
    IdxQ = read_int(f)
    start = read_int(f)
    name_start = read_int(f)

    f.seek(start)
    for _ in range(IdxQ):
        name_offset = read_int(f)
        offset = read_int(f)
        uncompressSize = read_int(f)
        size = read_int(f)
        entries.append((name_offset, offset, uncompressSize, size))

    for name_offset, offset, uncompressSize, size in entries:
        name = read_string(f, name_start + name_offset)
        #filename = os.path.basename(name)
        filename = name.replace('/', '\\')
        print(name, os.path.dirname(filename))
        os.makedirs(output_dir +"/"+  os.path.dirname(filename), exist_ok=True)
        rebuild[filename] = name
        
        f.seek(offset)
        data = f.read(size)
        #compstate = False
        #if filename.endswith(('.tbl', '.dat', '.txt')):
        #    compstate = uncompress(data, output_dir, filename)
        compstate = uncompress(data, output_dir, filename)
        if not compstate:
                write_output(output_dir, filename, data)
        
    return rebuild

def process_pidx0(filename, output_dir):
    with open(filename, 'rb') as f:
        if f.read(4).decode('ascii') != 'PIDX':
            print("无效的PIDX文件头")
            return


        if read_int(f,0x8) != 1:
            print('错误：无效的IDX文件')
            return

        start = read_int(f, 0xC)
        IdxQ = read_int(f, 0x10)
        name_start = read_int(f, 0x20)
        sub_index_count = read_int(f, 0x50)
        f.seek(0)
        list["start"] = f.read(start).hex()

        sub_index_pointers = []
        sub_index_start = start + 4
        for i in range(sub_index_count):
            pointer = read_int(f, sub_index_start + i*4)
            sub_index_pointers.append(pointer + start)

        for pointer in sub_index_pointers:
            name_offset = read_int(f, pointer)
            占位 = read_int(f, pointer + 4)
            fst_offset = read_int(f, pointer + 8)
            fst_size = read_int(f, pointer + 12)
            num = read_int(f, pointer + 16)
            
            name = read_string(f, name_start + name_offset)
            print(name)
            
            f.seek(fst_offset)
            fst_data = f.read(fst_size)
            
            sub_output = os.path.join(output_dir, name)
            list[name] = process_fsts(fst_data, sub_output)

    with open(os.path.join(output_dir,'list.json'), 'w', encoding='utf-8') as f:
        json.dump(list, f, indent=4)

def main(input_path, output_dir):
    if not os.path.exists(input_path):
        print("输入路径不存在")
        return

    if os.path.isfile(input_path) and input_path.lower().endswith('.dat'):
        process_pidx0(input_path, output_dir)
    elif os.path.isfile(input_path) and input_path.lower().endswith('.fsts'):
        with open(input_path, 'rb') as f:
            process_fsts(f.read(), output_dir)
    else:
        print("不支持的文件类型")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python script.py <输入文件/目录> <输出目录>")
    else:
        list = {}
        main(sys.argv[1], sys.argv[2])

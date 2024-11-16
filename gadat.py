import os
import sys
import json
import pandas as pd

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

def pack(input_dir, packname):
    try:
        with open(input_dir + '/json/idx.json', 'r', encoding='utf-8') as file:
            idx = pd.json_normalize(json.load(file))
    except FileNotFoundError:
        print(f"文件未找到: {input_dir}/json/idx.json")
        return
    except json.JSONDecodeError:
        print(f"文件不是有效的 JSON 格式: {input_dir}/json/idx.json")
        return
    except Exception as e:
        print(f"读取文件时发生错误: {e}")
        return
    data = bytearray()
    data[0:] = bytes.fromhex(idx['start'][0][0])
    IdxQ = read_int(data, 0x10)
    data[read_int(data, 0x18):] = b'\x00' * 6 * 4 * IdxQ
    idx_start = read_int(data, 0xC)
    data[read_int(data, 0x18):] = b'\x00' * read_int(data, 0x1C)
    filename_start = len(data)
    write_int(data, filename_start, 0x20)
    for content in idx['idx']:
        data.extend(packname.encode()+b'\x00')
        wirte_add = idx_start
        for type, sign, offset, filename, compstate in content:
            write_int(data, int(type, 16), wirte_add)
            write_int(data, len(data) - filename_start, wirte_add + 4)
            if int(type, 16) == 1:
                write_int(data, int(sign, 16), wirte_add + 4 * 2)
                write_int(data, int(offset, 16), wirte_add + 4 * 3)
            data.extend(filename.encode()+b'\x00')
            wirte_add += 6 * 4

        wirte_add = idx_start + 3 * 4
        
        for type, sign, offset, filename, compstate in content:
            if compstate and type == 0:
                with open(filename, 'rb') as f:
                        Udata = f.read()
                result = Udata, len(Udata), len(Udata)
            else:
                result =  compress(os.path.join(input_dir, filename)) #压缩文件
                    
            alignments = [0x1000, 0x800]
            current_alignment_index = 0
            if result:
                alignment = alignments[current_alignment_index]
    
    # 计算需要填充的字节数
                padding_size = (alignment - (len(data) % alignment)) % alignment
    
    # 如果padding_size为0，说明已经是对齐的，不需要填充
                if padding_size > 0:
                    data.extend(b'\x00' * padding_size)
                compresseddata, compresssize, UncompressedSize = result
                if compresseddata != None:
                    write_int(data, len(data), wirte_add)
                    write_int(data, compresssize, wirte_add + 4)
                    write_int(data, UncompressedSize, wirte_add + 4 * 2)
                    data.extend(compresseddata+b'\x00')
                wirte_add += 6 * 4

    #len(content)
    with open(packname, 'wb') as f:
            f.write(data)
    print('打包完毕 >> ' + packname)
    

def compress(input_file):
    if not os.path.isfile(input_file):
        return None, 0, 0
    with open(input_file, 'rb') as f:
        data = f.read()

    size = len(data)
    compresseddata = bytearray()

    # 添加文件头信息，使用 ' 3;0' 表示固定8字节算法
    compresseddata.extend(b' 3;0')
    compresseddata.extend(size.to_bytes(4, byteorder='little'))

    # 压缩逻辑：固定8字节简单异或
    for i in range(size):
        compressed_byte = data[i] ^ 0x72
        compresseddata.append(compressed_byte)
        
    return compresseddata, len(compresseddata), size

def uncompress(data, output_file):
    # 读取输入文件的字节数据和原始大小
    param_2 = int.from_bytes(data[4:8], 'little')  # 从文件中读取期待的原始大小

    # 初始化变量
    param_4 = len(data)
    iVar4 = 8
    iVar11 = 0
    uVar7 = 0xfee
    uVar10 = 0
    abStack_1020 = bytearray(0x1020)  # 缓冲区

    # 输出数据存储
    uncompress_data = bytearray()

    # 检查文件头，假设前三个字节决定解压缩方式
    compstate = False
    #if len(data) > 3 and (data[0] == ord('A') and data[1] == ord('R') and data[2] == ord('Z')): #这种文件头还没遇到，先留着
    if len(data) > 3 and (data[1] == ord('3') and data[2] == ord(';') and data[3] == ord('1')): # 使用控制字节的解压缩逻辑
        while True:
            while True:
                uVar10 >>= 1
                uVar6 = uVar10
                if (uVar10 & 0x100) == 0:
                    if param_4 <= iVar4:
                        # 写出结果
                        with open(output_file, 'wb') as f:
                            f.write(uncompress_data)
                        return True

                    pbVar8 = data[iVar4]
                    iVar4 += 1
                    uVar10 = (pbVar8 ^ 0x72) | 0xff00
                    uVar6 = pbVar8 ^ 0x72

                if (uVar6 & 1) != 0:
                    break

                if param_4 <= iVar4 + 1:
                    with open(output_file, 'wb') as f:
                        f.write(uncompress_data)
                    return True

                iVar9 = iVar4 + 1
                bVar1 = data[iVar4]
                iVar4 += 2
                bVar2 = data[iVar9]
                iVar9 = 0

                # 循环解密
                while iVar9 <= ((bVar2 ^ 0x72) & 0xf) + 2:
                    uVar6 = (bVar1 ^ 0x72 | ((bVar2 ^ 0x72) & 0xf0) << 4) + iVar9
                    iVar9 += 1
                    bVar3 = abStack_1020[uVar6 & 0xfff]
                    if iVar11 >= param_2:  # 使用param_2作为解密数据的长度限制
                        break
                    uncompress_data.append(bVar3)
                    abStack_1020[uVar7] = bVar3
                    uVar7 = (uVar7 + 1) & 0xfff
                    iVar11 += 1

            # 继续处理剩余的数据
            if param_4 <= iVar4:
                break
            bVar1 = data[iVar4]
            iVar4 += 1
            uncompress_byte = bVar1 ^ 0x72
            if iVar11 >= param_2:  # 使用param_2作为解密数据的长度限制
                break
            uncompress_data.append(uncompress_byte)
            abStack_1020[uVar7] = uncompress_byte
            uVar7 = (uVar7 + 1) & 0xfff
            iVar11 += 1
    elif len(data) > 3 and (data[1] == ord('3') and data[2] == ord(';') and data[3] == ord('0')):
        # 固定8字节处理的解压缩逻辑
        if 8 < param_4:
            for i in range(8, param_4):
                uncompress_byte = data[i] ^ 0x72
                if iVar11 >= param_2:
                    break
                uncompress_data.append(uncompress_byte)
                iVar11 += 1
    else:
        uncompress_data = data #若文件头不匹配，就以原始文件写出，记得在list表里标注打包时不要压缩
        compstate = True

    # 写出最终的解密结果
    with open(output_file, 'wb') as f:
        f.write(uncompress_data)
    if compstate:
        return False
    else:
        return True

def unpack(filename,output_dir):
    
    with open(filename, 'rb') as f:
        magic = f.read(5)
        if magic.decode('ascii') != 'PIDX0':
            print("文件头不符")
            return
        f.seek(0x8)
        if read_int(f) != 1:
            print('又调皮了哈？可不兴对idx用这个啊')
            return
        folder_log = []
        file_log = []
        entries = []
        rebuild = {'start': [],'idx':[]}
        f.seek(0xC) 
        start = read_int(f) #索引起始地址
        folder_log.append(f'索引起始地址：{hex(start)}')
        f.seek(0x10)
        IdxQ = read_int(f) #总索引数量
        folder_log.append(f'总索引数量：{IdxQ}')
        f.seek(0x20)
        name_start = read_int(f) #文件名起始地址
        folder_log.append(f'文件名起始地址：{hex(name_start)}\n\n文件夹：')
        f.seek(0)
        rebuild['start'].append(f.read(start).hex())
            
        f.seek(start)
        for i in range(IdxQ):
            type = read_int(f) #类型 若此值为1为文件夹
            name_offset = read_int(f)
            sign = read_int(f) #若为文件夹为该文件夹内文件数量
            offset = read_int(f) #在对应dat文件中起始偏移量
            UncompressedSize = read_int(f)
            size = read_int(f)
            entries.append((i, type, name_offset, sign, offset,  UncompressedSize ,size))
            
        count_file = 0
        count_folder = 0
        compstate = False
        for i, type, name_offset, sign, offset,  UncompressedSize, size in entries:
            f.seek(name_offset + name_start)
            buffer = f.read(20)
            null_index = buffer.find(b'\x00')
            filename = buffer[:null_index].decode('utf-8', errors='ignore') if null_index != -1 else buffer.decode('utf-8', errors='ignore')
            f.seek(offset)
            data = f.read(size)
            #print(f"{i+1}: {hex(type)} {hex(name_offset)} {hex(sign)} {hex(offset)} {hex(UncompressedSize)} {hex(size)} {filename}")
            if type == 1:
                count_folder += 1
                #output_subdir = os.path.join(output_dir, filename)
                #if not os.path.exists(output_subdir):
                #    os.makedirs(output_subdir)
                print(f"{count_folder}: {filename} （目录）")
                folder_log.append((f"{count_folder}: {hex(type)} {hex(name_offset)} {hex(sign)} {hex(offset)} {hex(UncompressedSize)} {hex(size)} {filename}"))
            else:
                count_file += 1
                compstate = uncompress(data,os.path.join(output_dir, filename))
                print(f"{count_file}: {filename}")
                file_log.append((f"{count_file}: {hex(type)} {hex(name_offset)} {hex(sign)} {hex(offset)} {hex(UncompressedSize)} {hex(size)} {filename}"))
            rebuild['idx'].append([hex(type), hex(sign), hex(offset), filename, compstate])
        json_dir = output_dir + '/json/'
        if not os.path.exists(json_dir):
            os.makedirs(json_dir)
        with open(json_dir + 'idx.json', 'w', encoding='utf-8') as f:
            json.dump(rebuild, f, indent=4)
        with open('unpack.log', 'w', encoding='utf-8') as f:
            f.write(f"{'\n'.join(folder_log)}\n\n文件：\n{'\n'.join(file_log)}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法：\n解包：目标文件 输出目录\n封包：打包目录 封包文件")
    else:
        if sys.argv[1].lower().endswith('.dat'):
            if not os.path.exists(sys.argv[2]):
                os.makedirs(sys.argv[2])
            print(f"目标文件: {sys.argv[1]}")
            unpack(sys.argv[1], sys.argv[2])
        else:
            pack(sys.argv[1],sys.argv[2])
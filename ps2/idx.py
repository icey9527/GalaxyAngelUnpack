import sys

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

def dat_up(dat_filename):
    with open(dat_filename, 'rb') as f:
        magic = f.read(5)
        if magic.decode('ascii') != 'PIDX0':
            print("文件头不符")
            return
        entries = []
        dat_dict = {}
        f.seek(0xC) 
        start = read_int(f) #索引起始地址
        f.seek(0x10)
        IdxQ = read_int(f) #总索引数量
        f.seek(0x20)
        name_start = read_int(f) #文件名起始地址

        f.seek(start)
        for i in range(IdxQ):
            type = read_int(f) #类型 若此值为1为文件夹
            name_offset = read_int(f)
            sign = read_int(f) #若为文件夹为该文件夹内文件数量
            offset = read_int(f) #文件中起始偏移量
            UncompressedSize = read_int(f)
            size = read_int(f)
            entries.append((i, type, name_offset, sign, offset,  UncompressedSize ,size))

        for i, type, name_offset, sign, offset,  UncompressedSize ,size in entries:
            f.seek(name_offset + name_start)
            buffer = f.read(20)
            null_index = buffer.find(b'\x00')
            filename = buffer[:null_index].decode('utf-8', errors='ignore') if null_index != -1 else buffer.decode('utf-8', errors='ignore')
            if type == 0:
                dat_dict[filename] = hex(offset),hex(UncompressedSize), hex(size)

        return dat_dict

def idx_up(dat_dict,idx_filename):
    with open(idx_filename, 'rb') as f:
        magic = f.read(5)
        if magic.decode('ascii') != 'PIDX0':
            print("文件头不符")
            return
        folder_log = []
        file_log = []
        entries = []
        f.seek(0xC)
        start = read_int(f) #索引起始地址
        folder_log.append(f'索引起始地址：{hex(start)}')
        f.seek(0x10)
        IdxQ = read_int(f) #总索引数量
        folder_log.append(f'总索引数量：{IdxQ}')
        f.seek(0x20)
        name_start = read_int(f) #文件名起始地址
        folder_log.append(f'文件名起始地址：{hex(name_start)}\n\n文件夹：')
            
        f.seek(start)
        for i in range(IdxQ):
            address = f.tell()
            type = read_int(f) #类型 若此值为1为文件夹
            name_offset = read_int(f)
            sign = read_int(f) #若为文件夹为该文件夹内文件数量
            offset = read_int(f) #在对应dat文件中起始偏移量
            UncompressedSize = read_int(f)
            size = read_int(f)
            entries.append((address, type, name_offset, sign, offset,  UncompressedSize ,size))

        count_file = 0
        count_folder = 0
        f.seek(0)
        data = bytearray(f.read())
        for address, type, name_offset, sign, offset,  UncompressedSize ,size in entries:
            f.seek(name_offset + name_start)
            buffer = f.read(20)
            null_index = buffer.find(b'\x00')
            filename = buffer[:null_index].decode('utf-8', errors='ignore') if null_index != -1 else buffer.decode('utf-8', errors='ignore')
            if type == 1:
                count_folder += 1
                #folder_log.append((f"{count_folder}: {hex(type)} {hex(name_offset)} {hex(sign)} {hex(offset)} {hex(UncompressedSize)} {hex(size)} {filename}"))
            else:
                count_file += 1
                #file_log.append((f"{count_file}: {hex(type)} {hex(name_offset)} {hex(sign)} {hex(offset)} {hex(UncompressedSize)} {hex(size)} {filename}"))

                if dat_dict.get(filename) is not None:
                    write_int(data, int(dat_dict[filename][0],16), address + 3 * 4)
                    write_int(data, int(dat_dict[filename][1],16), address + 4 * 4)
                    write_int(data, int(dat_dict[filename][2],16), address + 5 * 4)
                    file_log.append((f"{filename} {dat_dict[filename][0]} {dat_dict[filename][1]} {dat_dict[filename][2]}"))

        with open('idx.log', 'w', encoding='utf-8') as log_file:
            log_file.write(f"{'\n'.join(folder_log)}\n\n文件：\n{'\n'.join(file_log)}")
        with open(idx_filename, 'wb') as f:
            f.write(data)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：目标dat文件 idx.dat文件")
    else:
        dat_filename = sys.argv[1]
        if len(sys.argv) == 3:
            idx_filename = sys.argv[2]
        else:
            idx_filename = 'idx.dat'
        dat_dict = dat_up(dat_filename)
        idx_up(dat_dict, idx_filename)
        print(f'{dat_filename} >> idx.dat 更正完毕')

import sys

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

def write_int(file, content, address=None):
    if address is not None:
        file.seek(address)
    file.write(content.to_bytes(4, 'little'))

def dat_up(dat_filename):
    with open(dat_filename, 'rb') as f:
        magic = f.read(4)
        if magic.decode('ascii') != 'PIDX':
            print("文件头不符")
            return
        
        entries = []
        dat_dict = {}

        start = read_int(f,0xC) #索引起始地址
        name_start = read_int(f,0x20) #文件名起始地址


        if read_int(f, 0x14) != 1:
            IdxQ = read_int(f,0x10) #总索引数量
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
                if type == 0:
                    filename = read_string(f, name_start + name_offset)
                    dat_dict[filename] =offset, UncompressedSize, size

        return True,dat_dict

def idx_up(dat_filename, idx_filename):
    
    with open(idx_filename, 'rb+') as f:
        dat标志数量 = read_int(f,0x8)
        if dat标志数量 == 1:
            print("错误的idx文件")
            return

        dat_type, dat_dict = dat_up(dat_filename)

        name_start = read_int(f,0x20) #文件名起始地址
        dat标志地址 = read_int(f,0x4)
        for i in range(read_int(f,0x8)):
            dat_str_offset = read_int(f, dat标志地址 + i * 32)
            dat_str = read_string(f, name_start + dat_str_offset)
            if dat_str == dat_filename:
                dat_sign = dat_str_offset
            
        if dat_sign is None:
            print("idx中没有此dat文件")
            return
        
        if dat_type:
            entries = []


            IdxQ = read_int(f,0x10) #总索引数量
            start = read_int(f,0xC)
            f.seek(start)
            for i in range(IdxQ):
                address = f.tell()
                type = read_int(f) #类型 若此值为1为文件夹
                name_offset = read_int(f)
                sign = read_int(f) #若为文件夹为该文件夹内文件数量
                offset = read_int(f) #在对应dat文件中起始偏移量
                UncompressedSize = read_int(f)
                size = read_int(f)
                
                if sign == dat_sign and type == 0:
                    entries.append((address, type, name_offset, sign, offset,  UncompressedSize ,size))
            
        f.seek(0)
        uu = 0
        for address, type, name_offset, sign, offset,  UncompressedSize ,size in entries:
            filename = read_string(f, name_start + name_offset)
            if filename in dat_dict:
                uu += 1
                write_int(f, dat_dict[filename][0], address + 3 * 4)
                write_int(f, dat_dict[filename][1], address + 4 * 4)
                write_int(f, dat_dict[filename][2], address + 5 * 4)
        


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：目标dat文件 idx.dat文件")
    else:
        dat_filename = sys.argv[1]
        if len(sys.argv) == 3:
            idx_filename = sys.argv[2]
        else:
            idx_filename = 'idx.dat'
        idx_up(dat_filename, idx_filename)
        print(f'{dat_filename} >> idx.dat 更正完毕')

import os
import sys
import subprocess

def decode_shift_jis(data, encoding='shift-jis'):
    null_index = data.find(b'\x00')
    if null_index != -1:
        data = data[:null_index]
    try:
        decoded_str = data.decode(encoding)
        return decoded_str
    except UnicodeDecodeError:
        print("解码 Shift-JIS 时出现错误")
        return None



def main():
    with open(input+ ".msh", 'rb') as msh_file, open(input +'.msb', 'rb') as msb_file:
        msh_file.seek(0xc)

        for i in range(999999):
            size = int.from_bytes(msh_file.read(4), 'little')
            编号 = str(int.from_bytes(msh_file.read(4), 'little')+1)
            地址 = int.from_bytes(msh_file.read(4), 'little')
            type = int.from_bytes(msh_file.read(4), 'little')
            if size == 0 or  type ==0:
                break
            msb_file.seek(地址)
            #print(size,编号,地址,type)
            data = msb_file.read(size)
            filename = decode_shift_jis(data[0x20:0x40])
            filename, suffix = os.path.splitext(filename)
            print(编号+ '.' + filename+'.wav')
            subprocess.run(["vgmstream-cli", "-o", f'{input}/{filename}.wav', "-s", 编号, input +'.msb'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)

if __name__ == "__main__":
    if len(sys.argv) == 2:
        input = sys.argv[1]
        os.makedirs(input, exist_ok=True)
        main()
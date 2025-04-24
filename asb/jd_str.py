import sys
import csv

def extract_shift_jis(buffer, offset):
    end = offset
    while end < len(buffer) and buffer[end] != 0:
        end += 1
    return buffer[offset:end].decode('shift-jis').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t').replace('↙', '\\n')


def extract_str(input_file: str, code_file: str, out_file: str) -> None:

    code = []
    with open(code_file, "r", encoding='utf-8',errors='ignore') as f:
        for line in f.readlines():
            addr, rest = line.split(':')
            parts = rest.strip().split()
            op = parts[0]
            arg = parts[1] if len(parts) > 1 else ''
            code.append((addr, parts[0], parts[1] if len(parts) > 1 else ""))
        
    with open(input_file, "rb") as f:
        f.seek(0x34)
        str_start = int.from_bytes(f.read(4), 'little')
        f.seek(str_start)
        str_data = f.read()
    

    文本记录 = []
    说话人 = "未知"
    临时表 = []

    for addr, op, arg in code:
        if arg != "":
            临时表.append((addr, op ,int(arg,16) ))
        else:
            临时表 =  []
    
        if op == "CALL_FUN_00242E50":
            
            if arg == "0x300000013" and len(临时表) >= 4:
                说话人 = 临时表[len(临时表)-4][2]
            

            if arg == "0x100000000":
                文本指针 = 临时表[len(临时表)-2][2]
                地址 = 临时表[len(临时表)-2][0]
                文本记录.append(( f'{hex(int(地址,16)+1)}_{hex(文本指针)}'  , extract_shift_jis(str_data, 文本指针), "",说话人))

            if arg == "0x300000002":
                for count, (addr_, op_, arg_) in enumerate(临时表, start=1):
                    if op_ == "PUSH_IMM32":
                        文本记录.append(( f'{hex(int(addr_,16)+1)}_{hex(arg_)}' , extract_shift_jis(str_data,arg_),"",f'选项{count}'))


            临时表 = []
    
    with open(out_file, "w", newline="",encoding='utf-8',errors='ignore') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_NONNUMERIC)
        for record in 文本记录:
            row = list(record)
            row.extend([""] * (4 - len(row)))
            writer.writerow(row)


import os

def generate_target_paths(asb_dir, txt_dir, csv_dir):
    """
    根据.asb文件生成对应的.txt和.csv文件路径
    
    参数:
        asb_dir (str): 存放.asb文件的目录
        txt_dir (str): 存放.txt文件的目录
        csv_dir (str): 存放.csv文件的目录
    
    返回:
        list: 每个元素是 (asb_path, txt_path, csv_path) 的元组
    """

    os.makedirs(csv_dir, exist_ok=True)

    # 遍历.asb文件
    for root, _, files in os.walk(asb_dir):
        for file in files:
            if file.lower().endswith('.asb'):
                asb_path = os.path.join(root, file)
                
                # 获取文件名（不带后缀）
                filename = os.path.splitext(file)[0]
                
                # 构建.txt和.csv路径
                txt_path = os.path.join(txt_dir, f"{filename}.txt")
                csv_path = os.path.join(csv_dir, f"{filename}.csv")
                
                extract_str(asb_path, txt_path, csv_path)
    


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("用法:  <asb目录> <txt目录> <输出目录>")
        sys.exit(1)
    generate_target_paths(sys.argv[1], sys.argv[2], sys.argv[3])
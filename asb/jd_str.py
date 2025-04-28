import sys
import json

def read_int(f, address=None):
    if address is not None:
        f.seek(address)
    return int.from_bytes(f.read(4), 'little')

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
        变量地址 = read_int(f,0x24)
        变量数 = read_int(f,0x28)
        str_start = read_int(f,0x34)
        str_size = read_int(f,0x38)
        f.seek(str_start)
        str_data = f.read(str_size)

        变量文本 = {}
        for i in range(0, 变量数* 20, 20):
            变量文本[hex(read_int(f, 变量地址 + i))] = []
        


    文本记录 = []
    说话人 = "未知"
    临时表 = []
    文本数 = {}
    内码变量文本 = {}
    

    for addr, op, arg in code:
        if arg != "":
            临时表.append((addr, op ,int(arg,16) ))
        else:
            临时表 =  []

        lookup_masks = {
            "LOOKUP_2ARGS": 0xFFFFFFFF,
            "LOOKUP_2ARGS_BYTE": 0xFFFF
            }

        if op in lookup_masks:
            指针 = (int(arg,16)>> 32) & lookup_masks[op]
            内码变量文本[hex(指针)] = [extract_shift_jis(str_data, 指针), hex(int(addr,16) + 5)]

    
        if op == "CALL_FUN_00242E50":
            
            偏移映射 = {
            "0x300000013": 4,
            "0x200000013": 3, 
            "0x400000013": 5
            }

            if arg in 偏移映射 and len(临时表) >= 偏移映射[arg]:
                说话人 = str(临时表[len(临时表)-偏移映射[arg]][2] & 0xFFFF)


            if arg == "0x300000014" and len(临时表) >= 4:
                说话人 = f"{临时表[len(临时表)-4][2] & 0xFFFF}：思考"

            if arg == "0x80000004b":
                说话人 = "旁白"
            

            if arg == "0x100000000":
                文本指针 = 临时表[len(临时表)-2][2]
                地址 = 临时表[len(临时表)-2][0]
                文本记录.append(( f'{hex(int(地址,16)+1)}_{hex(文本指针)}'  , extract_shift_jis(str_data, 文本指针), 说话人))
                文本数[hex(文本指针)] = []

            选项表 = ["0x300000002","0x400000001","0x300000001","0x200000001","0x200000002","0x400000002","0x600000001","0x500000001","0x600000002","0x100000002"]

            if arg in 选项表:
                for count, (addr_, op_, arg_) in enumerate(临时表, start=1):
                    if op_ == "PUSH_IMM32":
                        文本数[hex(arg_)] = []
                        文本记录.append(( f'{hex(int(addr_,16)+1)}_{hex(arg_)}' , extract_shift_jis(str_data,arg_),f'选项{count}'))


            临时表 = []

    json_data = []
    for record in 文本记录:
        # 确保每行至少有2个元素（key和original）
        if len(record) >= 2:
            entry = {
                "key": record[0].strip(),      # 第1列 -> key
                "original": record[1].strip(),  # 第2列 -> original
                "translation":"",
                "stage": 0,
            }
            # 如果有第3列且不为空，则作为context
            if len(record) >= 3 and record[2].strip():
                entry["context"] = record[2].strip()
            json_data.append(entry)
    
    with open(out_file, "w", encoding='utf-8', errors='ignore') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)

    全部文本 = {hex(起始地址):段.decode('shift-jis') for 起始地址,段 in zip([0]+[sum(len(p)+1 for p in str_data.split(b'\x00')[:i]) for i in range(1,len(str_data.split(b'\x00')))], str_data.split(b'\x00')) if 段}
    漏网 = {k:全部文本[k] for k in 全部文本 if k not in 文本数}
    漏网 = {k:漏网[k] for k in 漏网 if k not in 变量文本}
    漏网 = {k:漏网[k] for k in 漏网 if k not in 内码变量文本}
    
    #del 漏网["0x0"]
    #for k in [k for k,v in 漏网.items() if str(v).startswith('@')]: del 漏网[k]

    if len(内码变量文本) != 0:
        return 内码变量文本


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
    
    漏网鱼 = {}

    # 遍历.asb文件
    for root, _, files in os.walk(asb_dir):
        for file in files:
            if file.lower().endswith('.asb'):
                asb_path = os.path.join(root, file)
                
                # 获取文件名（不带后缀）
                filename = os.path.splitext(file)[0]
                
                # 构建.txt和.csv路径
                txt_path = os.path.join(txt_dir, f"{filename}.txt")
                csv_path = os.path.join(csv_dir, f"{filename}.json")
                
                漏网之鱼 = extract_str(asb_path, txt_path, csv_path)
                if 漏网之鱼:
                    漏网鱼[filename] = (漏网之鱼)


    with open("内码变量.json", "w+", encoding='utf-8', errors='ignore') as f:
        json.dump(漏网鱼, f, ensure_ascii=False, indent=2)
    


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("用法:  <asb目录> <txt目录> <输出目录>")
        sys.exit(1)
    generate_target_paths(sys.argv[1], sys.argv[2], sys.argv[3])

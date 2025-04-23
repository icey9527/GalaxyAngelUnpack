import sys
from typing import Dict, List, Tuple

OPCODE_TO_PSEUDO_ASM: Dict[int, Tuple[str, int]] = {
    # 基础操作
    0x00: ("NOP", 0),                     # 无操作
    0x01: ("PUSH_IMM32", 4),              # 压入4字节立即数
    0x02: ("PUSH_TABLE_BYTE", 1),         # 压入表[byte]的值
    0x03: ("CALL_FUNC_22", 4),            # 调用 puVar26[0x22](imm32)
    0x04: ("CALL_FUNC_24", 4),            # 调用 puVar26[0x24](imm32)
    0x05: ("PUSH_REG9", 0),               # 压入 puVar26[9] 的值
    0x06: ("POP", 0),                     # 弹出栈顶
    0x07: ("STORE_TABLE_BYTE", 1),        # 表[byte] = 栈顶值
    0x08: ("CALL_FUNC_21", 4),            # 调用 puVar26[0x21](imm32)
    0x09: ("CALL_FUNC_23_BOOL", 4),       # 调用 puVar26[0x23](imm32)，结果转布尔
    0x0A: ("STORE_TABLE_BYTE_IMM32", 5),  # 表[byte] = imm32（1字节索引 + 4字节值）
    0x0B: ("CALL_FUNC_21_2ARGS", 8),      # 调用 puVar26[0x21](imm32, imm32)
    0x0C: ("CALL_FUNC_23_BOOL_2ARGS", 8), # 调用 puVar26[0x23](imm32, imm32)，结果转布尔
    0x0D: ("INC_TABLE_BYTE", 1),          # 表[byte]++
    0x0E: ("DEC_TABLE_BYTE", 1),          # 表[byte]--
    0x0F: ("CALL_FUNC_22_INC", 4),        # 调用 puVar26[0x22](imm32)，结果+1后调用 puVar26[0x21]
    0x10: ("CALL_FUNC_22_DEC", 4),        # 调用 puVar26[0x22](imm32)，结果-1后调用 puVar26[0x21]
    
    # 栈操作与算术
    0x11: ("SWAP", 0),                    # 交换栈顶两个值
    0x12: ("NEG", 0),                     # 栈顶值取负
    0x13: ("ADD", 0),                     # 栈顶两个值相加
    0x14: ("SUB", 0),                     # 栈顶两个值相减
    0x15: ("MUL", 0),                     # 栈顶两个值相乘
    0x16: ("DIV", 0),                     # 栈顶两个值相除
    0x17: ("MOD", 0),                     # 栈顶两个值取模
    0x18: ("AND", 0),                     # 栈顶两个值按位与
    0x19: ("OR", 0),                      # 栈顶两个值按位或
    0x1A: ("NOT", 0),                     # 栈顶值按位取反
    0x1B: ("EQ", 0),                      # 栈顶两个值是否相等
    0x1C: ("NEQ", 0),                     # 栈顶两个值是否不等
    0x1D: ("LT", 0),                      # 栈顶值1 < 栈顶值2
    0x1E: ("GT", 0),                      # 栈顶值1 > 栈顶值2
    0x1F: ("LTE", 0),                     # 栈顶值1 <= 栈顶值2
    0x20: ("GTE", 0),                     # 栈顶值1 >= 栈顶值2
    
    # 控制流
    0x21: ("JMP", 4),                     # 无条件跳转到 imm32
    0x22: ("JZ", 4),                      # 栈顶为0则跳转到 imm32
    0x23: ("JNZ", 4),                     # 栈顶非0则跳转到 imm32
    0x24: ("SWITCH", 5),                  # 根据 byte 跳转（1字节索引 + 4字节地址）
    0x25: ("CALL_FUN_00243200", 4),       # 调用外部函数 FUN_00243200(imm32)
    0x26: ("LOOKUP_2ARGS", 8),            # 双参数查找（imm32, imm32）
    0x27: ("LOOKUP_BYTE", 5),             # 查找（imm32 + byte）
    0x28: ("LOOKUP_2ARGS_BYTE", 9),       # 双参数查找（imm32, imm32, byte）
    0x29: ("CALL_FUN_00242E50", 5),       # 调用外部函数 FUN_00242E50(imm32, byte)
    0x2A: ("STORE_REG9", 0),              # puVar26[9] = 栈顶值
    0x2B: ("RESET_FRAME", 0),             # 重置栈帧（puVar26[9] = 0）
    0x2C: ("EXIT", 0),                    # 终止执行
}


def parse_binary_file(input_file: str, output_file: str) -> None:
    with open(input_file, "rb") as f:
        f.seek(0x2c)
        start = int.from_bytes(f.read(4), 'little') # 索引起始地址
        
        f.seek(0x30)
        end = int.from_bytes(f.read(4), 'little')
        #str_start = int.from_bytes(f.read(4), 'little')
        f.seek(start)
        all = f.read()
        data = all[start:end]
        #str_data = all[str_start:]

    pc = 0
    output_lines = []

    while pc < len(data):
        
        opcode = data[pc]
        pc += 1

        if opcode not in OPCODE_TO_PSEUDO_ASM:
            #output_lines.append(f"0x{pc-1:04X}: [ERROR] 未知操作码 0x{opcode:02X}")
            continue

        op_name, param_size = OPCODE_TO_PSEUDO_ASM[opcode]
        params = []

        if param_size > 0:
            if pc + param_size > len(data):
                #output_lines.append(f"0x{pc-1:04X}: [ERROR] 操作码 0x{opcode:02X} 参数越界")
                break
            params = list(data[pc:pc+param_size])
            pc += param_size

        if param_size > 0:
        # 将字节列表转换为小端序数字
            param_value = int.from_bytes(bytes(params), 'little')
            param_str = f"{hex(param_value)}"
        else:
            param_str = ""
        #output_lines.append(f"0x{pc-1-len(params)-1:04X}: {op_name} {param_str}")
        output_lines.append(f"0x{pc-1-len(params) + start* 2:04X}: {op_name} {param_str}") # 我也不知道为啥要乘2

    with open(output_file, "w",encoding='utf-8',errors='ignore') as f:
        f.write("\n".join(output_lines))



import os

def generate_target_paths(asb_dir, txt_dir):
    """
    根据.asb文件生成对应的.txt和.csv文件路径
    
    参数:
        asb_dir (str): 存放.asb文件的目录
        txt_dir (str): 存放.txt文件的目录
        csv_dir (str): 存放.csv文件的目录
    
    返回:
        list: 每个元素是 (asb_path, txt_path, csv_path) 的元组
    """

    os.makedirs(txt_dir, exist_ok=True)

    # 遍历.asb文件
    for root, _, files in os.walk(asb_dir):
        for file in files:
            if file.lower().endswith('.asb'):
                asb_path = os.path.join(root, file)
                
                # 获取文件名（不带后缀）
                filename = os.path.splitext(file)[0]
                
                # 构建.txt和.csv路径
                txt_path = os.path.join(txt_dir, f"{filename}.txt")
                
                
                parse_binary_file(asb_path, txt_path)



if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("用法:  <输入目录> <输出目录>")
        sys.exit(1)
    generate_target_paths(sys.argv[1], sys.argv[2])

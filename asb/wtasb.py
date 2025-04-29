import sys
import json
import os
import re




def load_code_table(code_table_path):
    """
    Load code table file and create a dictionary
    - 过滤所有数字（全角/半角）
    - 过滤所有字母（全角/半角）
    - 过滤标点符号
    - 只保留汉字和其他非字母数字字符
    """
    code_dict = {}
    with open(code_table_path, 'r', encoding='utf-16-le') as f:
        for line in f:
            line = line.strip()
            if '=' in line:
                code, char = line.split('=', 1)
                code = code.strip().lower()
                char = char.strip()
                
                if char:
                    cp = ord(char[0])
                    is_halfwidth_digit = 0x0030 <= cp <= 0x0039
                    is_halfwidth_alpha = (0x0041 <= cp <= 0x005A) or (0x0061 <= cp <= 0x007A)
                    is_fullwidth_digit = 0xFF10 <= cp <= 0xFF19
                    is_fullwidth_alpha = (0xFF21 <= cp <= 0xFF3A) or (0xFF41 <= cp <= 0xFF5A)
                    
                    if (not re.search(r'[^\w\s]', char) and
                        not is_halfwidth_digit and
                        not is_halfwidth_alpha and
                        not is_fullwidth_digit and
                        not is_fullwidth_alpha):
                        code_dict[char] = code
    return code_dict

def convert_to_shiftjis(text):
    """
    将中文字符转换为Shift-JIS编码表示，包含标点替换和编码验证
    """
    replace_rules = {
        '·': '・',
        '—': '－',
        '～': '〜',
        '“': '「',
        '”': '」',
        '：': '：',
        '；': '；',
        ' ': '　'
    }

    text_blocks = text.split('\n')  # 修正换行符分割逻辑
    converted_blocks = []
    
    for block in text_blocks:
        block_result = []
        for char in block:
            replaced_char = replace_rules.get(char, char)
            try:
                if replaced_char in code_dict:
                    code = code_dict[replaced_char]
                    byte_pair = bytes.fromhex(code)
                    decoded_char = byte_pair.decode('CP932')  # 修正编码名称
                    block_result.append(decoded_char)
                else:
                    replaced_char.encode('CP932')
                    block_result.append(replaced_char)
            except (UnicodeEncodeError, KeyError):
                print(f"非法字符: [{replaced_char}] (原始字符: [{char}])，已替换为?")
                block_result.append('?')
        converted_blocks.append(''.join(block_result))
    
    return '\n'.join(converted_blocks)










def extract_CP932(buffer, offset):
    end = offset
    while end < len(buffer) and buffer[end] != 0:
        end += 1
    return buffer[offset:end].decode('shift-jis').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t').replace('↙', '\\n')

def encode_shiftjis(text: str, use_convert: bool = True) -> bytes:
    if not text:
        return b'\x00'
    if use_convert:
        text = convert_to_shiftjis(text.replace('\\n', '\n').replace('\\r', '\r'))
    else:
        text = text.replace('\\n', '\n').replace('\\r', '\r')
    return text.encode('CP932') + b'\x00'


def extract_str(input_file: str, json_file: str, out_file: str, 内码变量文本=None) -> None:

    with open(input_file, "rb") as f:
        data = f.read()
        f.seek(0x34)
        str_start = int.from_bytes(f.read(4), 'little')
        f.seek(0x3C)
        next_asb = int.from_bytes(f.read(4), 'little')
        if os.path.getsize(input_file) > next_asb:
            next_asbname = extract_CP932(data,next_asb)
        else:
            next_asbname =  next_asb - os.path.getsize(input_file)
        f.close()

    index_data = bytearray(data[:str_start])
    str_data = data[str_start:]

    未翻译 = False
    min_value = len(str_data)
    result_dict = {}

    with open(json_file, "r", encoding='utf-8') as f:
        data = json.load(f)

    for item in data:
        if "key" not in item or "translation" not in item:
            continue

        hex_str,str_idx = item["key"].split("_", 1)
        try:
            num = int(hex_str, 16)
            str_idx = int(str_idx, 16)
        except (ValueError, AttributeError):
            continue

        if str_idx < min_value:
            min_value = str_idx

    
        if item["translation"] == '':
            未翻译 = True
            key = item["original"]
        else:
            key = item["translation"]
        
        if key in result_dict:
            result_dict[key].append(num)
        else:
            result_dict[key] = [num]
    
    if 未翻译:
        print(f"{json_file}有未翻译的内容")

    if min_value == len(str_data):
        print(f"{json_file}未找到最小值")

    str_data_h = str_data[:min_value]

    for key, addres in result_dict.items():
        for addr in addres:
            index_data[addr : addr + 4] = len(str_data_h).to_bytes(4, byteorder='little', signed=False)
        str_data_h += encode_shiftjis(key)

    if 内码变量文本:
        for value in 内码变量文本.values():
            wirte_addr = int(value[1],16)
            index_data[wirte_addr : wirte_addr + 4] = len(str_data_h).to_bytes(4, byteorder='little', signed=False)
            str_data_h += encode_shiftjis(value[0],False)
    
    str_size = len(str_data_h)
    index_data[0x38 : 0x38 + 4] = str_size.to_bytes(4, byteorder='little', signed=False)
    if type(next_asbname) == str:
        index_data[0x3C : 0x3C + 4] = (str_start + str_size).to_bytes(4, byteorder='little', signed=False)
        str_data_h += encode_shiftjis(next_asbname)
    else:
        index_data[0x3C : 0x3C + 4] = (len(index_data + str_data_h)).to_bytes(4, byteorder='little', signed=False)
    new_data = index_data + str_data_h
    with open(out_file, 'wb') as f:  # 'wb' 表示二进制写入模式
        f.write(new_data)
    
    









def generate_target_paths(asb_dir, json_dir, new_dir):
    
    os.makedirs(new_dir, exist_ok=True)

    # 遍历.asb文件
    for root, _, files in os.walk(json_dir):
        for file in files:
            if file.lower().endswith('.json'):
                json_path = os.path.join(root, file)
                
                # 获取文件名（不带后缀）
                filename = os.path.splitext(file)[0]
                
                # 构建.txt和.json路径
                asb_path = os.path.join(asb_dir, f"{filename}.asb")
                new_path = os.path.join(new_dir, f"{filename}.asb")
                if filename in 内码变量:
                    extract_str(asb_path, json_path, new_path, 内码变量[filename])
                else:
                    extract_str(asb_path, json_path, new_path)
    


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("用法:  <asb目录> <json目录> <输出目录>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]
    code_table_path = "TargetTblFile.tbl"
    with open("内码变量.json", "r", encoding='utf-8') as f:
        内码变量 = json.load(f)
    
    try:
        code_dict = load_code_table(code_table_path)
    except Exception as e:
        print(f"加载码表失败: {e}")
        sys.exit(1)

    generate_target_paths(sys.argv[1], sys.argv[2], sys.argv[3])

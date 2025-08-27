import json
import os
import re
import shutil
import sys
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

def convert_to_shiftjis(text, code_dict):
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

def read_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def read_tbl_file(file_path):
    lines = []
    with open(file_path, 'r', encoding='CP932') as file:
        for line in file:
            lines.append(line)
    return lines

def parse_json_key(json_key):
    match = re.match(r'(.+)\[(.+)\](.+)', json_key)
    if match:
        file_name, section, key = match.groups()
        return file_name, section, key
    return None, None, None

def apply_translations(original_tbl_lines, translations):
    # Group translations by section and key
    translation_map = {}
    for item in translations:
        _, section, key = parse_json_key(item['key'])
        if section and key:
            if section not in translation_map:
                translation_map[section] = {}
            # Use translation if it exists, otherwise use original
            text = convert_to_shiftjis(item['translation'], code_dict) if item['translation'] else item['original']
            translation_map[section][key] = text
    
    # Apply translations to the original lines
    current_section = None
    new_lines = []
    
    for line in original_tbl_lines:
        original_line = line
        line_content = line.strip()
        
        # Skip comments and empty lines
        if not line_content or '\\' in line_content:
            new_lines.append(original_line)
            continue
            
        # Handle comments at the end of lines
        comment_part = ""
        if '//' in line_content:
            line_parts = line_content.split('//', 1)
            line_content = line_parts[0].strip()
            comment_part = "//" + line_parts[1]
        
        # Handle semicolons
        semicolon_part = ""
        if ';' in line_content:
            line_parts = line_content.split(';', 1)
            line_content = line_parts[0].strip()
            semicolon_part = ";" + line_parts[1]
        
        # Check for section headers
        if line_content.startswith('[') and line_content.endswith(']'):
            current_section = line_content[1:-1]
            new_lines.append(original_line)
            continue
        
        # Handle key-value pairs
        if '=' in line_content and current_section:
            key, value = line_content.split('=', 1)
            key = key.strip()
            value = value.strip()
            
            # Replace value if it exists in our translation map
            if current_section in translation_map and key in translation_map[current_section]:
                new_value = translation_map[current_section][key]
                # Recreate the line with the new value and preserve formatting
                indent = re.match(r'^\s*', original_line).group(0)
                new_line = f"{indent}{key} ={new_value}"
                if comment_part:
                    new_line += f" {comment_part}"
                if semicolon_part:
                    new_line += f" {semicolon_part}"
                new_line += "\n"
                new_lines.append(new_line)
                continue
        
        # If no changes were made, keep the original line
        new_lines.append(original_line)
    
    return new_lines

def write_tbl_file(file_path, lines):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='CP932') as file:
        file.writelines(lines)



def process_reverse(original_folder, json_folder, output_folder):
    # First, copy the entire original folder structure to the output folder
    if os.path.exists(output_folder):
        shutil.rmtree(output_folder)
    shutil.copytree(original_folder, output_folder)
    
    # Then find all JSON files and apply the translations
    for root, dirs, files in os.walk(json_folder):
        rel_path = os.path.relpath(root, json_folder)
        
        for file in files:
            if file.endswith('.tbl.json'):
                json_path = os.path.join(root, file)
                tbl_file_name = file[:-5]  # Remove .json suffix

                if '■' in tbl_file_name:
                    dir_part, file_part = tbl_file_name.split('■', 1)
                    if file_part == "slg_stageinfo.tbl":
                        original_tbl_path = os.path.join(original_folder, dir_part, "slg", file_part)
                        output_tbl_path = os.path.join(output_folder, dir_part, "slg", file_part)
                    elif file_part == "stage.tbl":
                        original_tbl_path = os.path.join(original_folder, dir_part, "slg", "stage", re.search(r'\d+',dir_part)[0], file_part)
                        output_tbl_path = os.path.join(output_folder, dir_part, "slg", "stage", re.search(r'\d+',dir_part)[0], file_part)
                        
                else:
                    original_tbl_path = os.path.join(original_folder, rel_path, tbl_file_name)
                    output_tbl_path = os.path.join(output_folder, rel_path, tbl_file_name)

            
                print(original_tbl_path)

                
                if os.path.exists(original_tbl_path):
                    # Read JSON translations
                    translations = read_json_file(json_path)
                    
                    # Read original TBL file
                    original_tbl_lines = read_tbl_file(original_tbl_path)
                    
                    # Apply translations
                    new_tbl_lines = apply_translations(original_tbl_lines, translations)
                    
                    # Write the new TBL file
                    write_tbl_file(output_tbl_path, new_tbl_lines)
                    print(f"Processed: {tbl_file_name}")
                else:
                    print(f"Original file not found: {original_tbl_path}")

# 使用示例
original_folder = 'slg'  # 原始tbl文件目录
json_folder = 'slg_tbl'  # JSON翻译文件目录
output_folder = 'new_slg'  # 输出翻译后的tbl文件目录

code_table_path = "TargetTblFile.tbl"
    
try:
    code_dict = load_code_table(code_table_path)
except Exception as e:
    print(f"加载码表失败: {e}")
    sys.exit(1)

process_reverse(original_folder, json_folder, output_folder)
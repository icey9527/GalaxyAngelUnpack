import json
import re
import os
import sys

def read_tbl_file(file_path):
    result = {}
    current_section = None
    with open(file_path, 'r', encoding='shift-jis',errors='ignore') as file:
        for line in file:
            line = line.strip()
            if '//' in line:
                line = line.split('//')[0].strip()
            if ';' in line:
                line = line.split(';')[0].strip()
            if not line or '\\' in line:
                continue
            if line.startswith('[') and line.endswith(']'):
                current_section = line[1:-1]
                result[current_section] = {}
            elif '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                if current_section:
                    result[current_section][key] = value
    return result

def contains_chinese_or_japanese(text):
    pattern = re.compile(r'[\u4e00-\u9fff\u3040-\u30ff\u31f0-\u31ff]')
    return bool(pattern.search(text))

def generate_json_data(tbl_data, file_name):
    json_data = []
    for section, items in tbl_data.items():
        for key, value in items.items():
            if contains_chinese_or_japanese(value):
                full_key = f"{file_name}[{section}]{key}"
                entry = {
                    "key": full_key,
                    "original": value,
                    "translation": "",
                    "stage": 0
                }
                json_data.append(entry)
    return json_data

def write_to_json(json_data, output_path):
    if len(json_data) > 0:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=4)

def process_folder(input_folder, output_folder):
    for root, dirs, files in os.walk(input_folder):
        rel_path = os.path.relpath(root, input_folder)
        for file in files:
            if file.endswith('.tbl'):
                file_path = os.path.join(root, file)
                tbl_data = read_tbl_file(file_path)
                json_data = generate_json_data(tbl_data, file)
                output_path = os.path.join(output_folder, f"{f"{os.path.basename(root)}■{file}"}.json")
                write_to_json(json_data, output_path)

# 使用示例
input_folder = sys.argv[1]
json_output_folder = sys.argv[2]
process_folder(input_folder, json_output_folder)

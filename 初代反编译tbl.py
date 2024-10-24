import struct
import sys
import os

def read_int(file, offset):
    file.seek(offset)
    return struct.unpack('<I', file.read(4))[0]

def read_string(file, offset):
    file.seek(offset)
    result = b''
    while True:
        char = file.read(1)
        if char == b'\x00' or not char:  # 如果读取到空字符或文件结束，则停止
            break
        result += char
    return result

def parse_iidx(file_path):
    with open(file_path, 'rb') as file:
        if not file.read(4) == b'IIDX':
            print(f"{file_path} 文件头不符，跳过")
            return
        section_count_offset = 4
        section_count = read_int(file, section_count_offset)
        
        # 计算键值数量偏移
        key_value_offset = 4 + 4 + section_count * 8
        
        # 读取键值数量
        key_value_count = read_int(file, key_value_offset)
        
        # 计算字符结束偏移
        char_end_offset = key_value_offset + 4 + key_value_count * 24
        char_start_offset = char_end_offset + 4
        
        # 存储节名和对应的键值对
        sections = {}
        
        # 遍历所有节
        section_start_offset = section_count_offset + 4
        for i in range(section_count):
            section_type_id = read_int(file, section_start_offset)
            section_name_offset = read_int(file, section_start_offset + 4)
            section_name = read_string(file, char_start_offset + section_name_offset)
            sections[section_type_id] = {"name": section_name, "keys": []}
            section_start_offset += 8  # 移动到下一个节的起始偏移
        
        # 遍历所有键值对
        key_value_start_offset = key_value_offset + 4
        for i in range(key_value_count):
            key_section_id = read_int(file, key_value_start_offset)
            key_id = read_int(file, key_value_start_offset + 4)
            padding = read_int(file, key_value_start_offset + 8)  # 占位值，无用
            key_offset = read_int(file, key_value_start_offset + 12)
            value_offset = read_int(file, key_value_start_offset + 16)
            next_key_offset = read_int(file, key_value_start_offset + 20)
            
            # 检查占位值是否为0xFFFFFFFF
            if padding != 0xFFFFFFFF:
                padding_dec = int(f"{padding:X}", 16)
                key_name = f"#{padding_dec}".encode() # 使用占位值作为键名
            else:
                key_name = read_string(file, char_start_offset + key_offset)
            value = read_string(file, char_start_offset + value_offset)    
            
            # 存储键值对和它们的值偏移量
            sections[key_section_id]["keys"].append((key_name, value, value_offset))
            
            key_value_start_offset += 24  # 移动到下一个键值对的起始偏移
        
        # 将键值对添加到对应的节，并根据值偏移量排序
        for section_id, content in sections.items():
            content["keys"].sort(key=lambda x: x[2])
        
        # 写入文件
        with open(file_path, "wb") as output_file:
            for section_id, content in sections.items():
                output_file.write(b"[" + content["name"] + b"]\n")
                for key, value, _ in content["keys"]:
                    output_file.write(b"=".join([key, value]) + b"\n")
                output_file.write(b'\n')
        
        print(f'文件 {os.path.basename(file_path)} 生成成功！\n共：\n{section_count}个节\n{key_value_count}对键值')

def process_directory(directory_path):
    if not os.path.exists(directory_path):
        print("指定的目录不存在")
        return
    
    for root, dirs, files in os.walk(directory_path):
        for file in files:
            if file.endswith('.tbl') or file.endswith('.idx') or file.endswith('.iidx'):
                file_path = os.path.join(root, file)
                parse_iidx(file_path)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python ga_all_tbl.py <directory_path>")
    else:
        directory_path = sys.argv[1]
        process_directory(directory_path)
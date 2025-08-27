import argparse
import os
import hashlib
import json
import shutil

def calculate_hash(filepath):
    """计算文件的哈希值"""
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def scan_png_files(root_dir):
    """扫描目录并返回PNG文件结构字典"""
    files_dict = {}
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith('.png'):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, root_dir)
                files_dict[rel_path] = full_path
    return files_dict

def extract_files(input_dir, output_dir):
    """提取模式：处理PNG文件并生成映射"""
    all_files = scan_png_files(input_dir)
    file_groups = {}
    path_mapping = {}

    # 按文件名和哈希分组
    for rel_path, full_path in all_files.items():
        filename = os.path.basename(rel_path)
        file_hash = calculate_hash(full_path)
        key = (filename, file_hash)
        
        if key not in file_groups:
            file_groups[key] = []
        file_groups[key].append(rel_path)

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    # 处理每个文件组
    for (filename, file_hash), paths in file_groups.items():
        # 处理可合并文件
        if len(paths) > 1:
            output_path = os.path.join(output_dir, filename)
            
            # 检查文件冲突
            if os.path.exists(output_path):
                existing_hash = calculate_hash(output_path)
                if existing_hash != file_hash:
                    raise ValueError(f"冲突文件：{filename} 已存在且内容不同")
            
            # 复制文件到根目录
            if not os.path.exists(output_path):
                shutil.copy2(all_files[paths[0]], output_path)
            
            path_mapping[filename] = paths
        # 处理独立文件
        else:
            original_path = paths[0]
            output_path = os.path.join(output_dir, original_path)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            if not os.path.exists(output_path):
                shutil.copy2(all_files[original_path], output_path)
            
            path_mapping[original_path] = [original_path]

    # 保存映射文件
    with open(os.path.join(output_dir, 'manifest.json'), 'w') as f:
        json.dump(path_mapping, f, indent=2)
    
    print(f"提取完成！共处理 {len(all_files)} 个PNG文件")

def replace_files(source_dir, target_dir):
    """替换模式：根据映射恢复文件"""
    manifest_path = os.path.join(source_dir, 'manifest.json')
    if not os.path.exists(manifest_path):
        raise FileNotFoundError("未找到 manifest.json 文件")

    with open(manifest_path) as f:
        path_mapping = json.load(f)

    for map_key, original_paths in path_mapping.items():
        source_path = os.path.join(source_dir, map_key)
        
        if not os.path.exists(source_path):
            print(f"警告：找不到源文件 {map_key}")
            continue

        for rel_path in original_paths:
            target_path = os.path.join(target_dir, rel_path)
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            shutil.copy2(source_path, target_path)
            print(f"已更新：{rel_path}")

def main():
    parser = argparse.ArgumentParser(description="PNG文件同步工具")
    subparsers = parser.add_subparsers(dest='command', required=True)

    # 提取模式
    extract_parser = subparsers.add_parser('extract', help='提取重复文件')
    extract_parser.add_argument('-i', '--input', required=True, help='原始目录')
    extract_parser.add_argument('-o', '--output', required=True, help='输出目录')

    # 替换模式
    replace_parser = subparsers.add_parser('replace', help='替换文件')
    replace_parser.add_argument('-s', '--source', required=True, help='修改后的目录')
    replace_parser.add_argument('-t', '--target', required=True, help='目标目录')

    args = parser.parse_args()

    if args.command == 'extract':
        extract_files(args.input, args.output)
    elif args.command == 'replace':
        replace_files(args.source, args.target)

if __name__ == '__main__':
    main()
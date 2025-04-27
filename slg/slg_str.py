import sys
import json

def extract_shift_jis(buffer, offset):
    end = offset
    while end < len(buffer) and buffer[end] != 0:
        end += 1
    return buffer[offset:end].decode('shift-jis').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t').replace('↙', '\\n')


def extract_str(input_file: str, out_file: str) -> None:

    with open(input_file, "rb") as f:
        data = f.read()
        f.seek(0)
        extracted_texts = []
        while True:
            if f.tell() + 4 > os.path.getsize(input_file):
                break
            code = int.from_bytes(f.read(4), 'little')
            if code == 0x85d:
                str_offset = int.from_bytes(f.read(4), 'little')
                sen = extract_shift_jis(data, str_offset)
                entry = {
                    "key": f"{hex(f.tell()-4)}_{hex(str_offset)}",
                    "original": sen
                }
                extracted_texts.append(entry)

    with open(out_file, 'w', encoding='utf-8') as json_f:
        json.dump(extracted_texts, json_f, ensure_ascii=False, indent=4)
    



import os

def generate_target_paths(in_dir, out_dir):
    os.makedirs(out_dir, exist_ok=True)

    # 遍历.asb文件
    for root, _, files in os.walk(in_dir):
        for file in files:
            if file.lower() == 'slg_opdemo.dat':
                in_path = os.path.join(root, file)

                filename = os.path.basename(root)

                out_path = os.path.join(out_dir, f"{filename}.json")
                
                extract_str(in_path, out_path)
    


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("用法:  <slg目录> <输出目录>")
        sys.exit(1)
    generate_target_paths(sys.argv[1], sys.argv[2])

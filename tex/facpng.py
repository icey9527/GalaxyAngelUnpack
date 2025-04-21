import struct
from PIL import Image
import sys
import os
from pathlib import Path

def read_binary_fac_image_8bpp(data):
    
    try:
        flag = data[0x48:0x49].hex()
        if  flag == '00':
            pixel_data_offset = 0x90
            width = struct.unpack('<H', data[0x78:0x7a])[0]
            height = struct.unpack('<H', data[0x7a:0x7c])[0]            
        elif flag == '01':
            pixel_data_offset = 0xb0
            width = struct.unpack('<H', data[0x98:0x9a])[0]
            height = struct.unpack('<H', data[0x9a:0x9c])[0]
        elif flag == '04':
            pixel_data_offset = 0xd0
            width = struct.unpack('<H', data[0xb8:0xba])[0]
            height = struct.unpack('<H', data[0xba:0xbc])[0]
        else:
            pixel_data_offset = 0xc0
            width = struct.unpack('<H', data[0xa8:0xaa])[0]
            height = struct.unpack('<H', data[0xaa:0xac])[0]        
        
        palette_offset = width * height + pixel_data_offset
        palette_data = data[palette_offset : palette_offset + 256 * 4]
        
        # 原始调色板处理（完全保持原有逻辑）
        original_palette = []
        for i in range(256):
            pos = i * 4
            r = palette_data[pos]
            g = palette_data[pos + 1]
            b = palette_data[pos + 2]
            a = palette_data[pos + 3]
            if a == 128:
                a = 255
            original_palette.append((r, g, b, a))
        
        # 调色板重排逻辑（完全保持原有算法）
        palette = []
        for major_group_start in range(0, 256, 32):  # 每32色一个大组
            major_group = original_palette[major_group_start:major_group_start+32]
            subgroup1 = major_group[0:8]    # 第1小组
            subgroup2 = major_group[8:16]   # 第2小组
            subgroup3 = major_group[16:24]  # 第3小组
            subgroup4 = major_group[24:32]  # 第4小组
            reordered_major_group = subgroup1 + subgroup3 + subgroup2 + subgroup4
            palette.extend(reordered_major_group)
        
        
        pixel_data = data[pixel_data_offset:]
        
        expected_size = width * height
        if len(pixel_data) < expected_size:
            raise ValueError("像素数据不足，无法填充指定的宽度和高度")

        # 创建RGBA图像
        img = Image.new('RGBA', (width, height))
        pixels = img.load()
        
        # 处理8bpp索引色到RGBA的转换
        for y in range(height):
            for x in range(width):
                index = pixel_data[y * width + x]
                r, g, b, a = palette[index]
                pixels[x, y] = (r, g, b, a)
        
        return img
        
    except Exception as e:
        print(f"处理8bpp文件时出错: {e}")
        return None

def read_binary_agi_image_8bpp(data):
    try:
        width = struct.unpack('<H', data[0x18:0x1a])[0]
        height = struct.unpack('<H', data[0x1a:0x1C])[0]
        
        palette_offset = data[0x1C] | (data[0x1D] << 8) | (data[0x1E] << 16)
        palette_data = data[palette_offset : palette_offset + 256 * 4]
        
        # 原始调色板
        original_palette = []
        for i in range(256):
            pos = i * 4
            r = palette_data[pos]
            g = palette_data[pos + 1]
            b = palette_data[pos + 2]
            a = palette_data[pos + 3]
            if a == 128:
                a = 255
            original_palette.append((r, g, b, a))
        
        # 重新排列调色板：
        # 1. 将256色分成8个大组（每个大组32色=4个小组×8色）
        # 2. 在每个大组内部，交换第2小组和第3小组的位置
        palette = []
        for major_group_start in range(0, 256, 32):  # 每32色一个大组
            major_group = original_palette[major_group_start:major_group_start+32]
            
            # 将大组分成4个小组（每组8色）
            subgroup1 = major_group[0:8]    # 第1小组
            subgroup2 = major_group[8:16]   # 第2小组
            subgroup3 = major_group[16:24]  # 第3小组
            subgroup4 = major_group[24:32]  # 第4小组
            
            # 交换第2和第3小组
            reordered_major_group = subgroup1 + subgroup3 + subgroup2 + subgroup4
            palette.extend(reordered_major_group)
        
        pixel_data_offset = 0x30
        pixel_data = data[pixel_data_offset:]
        
        expected_size = width * height
        if len(pixel_data) < expected_size:
            raise ValueError("像素数据不足，无法填充指定的宽度和高度")

        # 创建RGBA图像
        img = Image.new('RGBA', (width, height))
        pixels = img.load()
        
        # 处理8bpp索引色到RGBA的转换
        for y in range(height):
            for x in range(width):
                index = pixel_data[y * width + x]
                r, g, b, a = palette[index]
                pixels[x, y] = (r, g, b, a)
        
        return img
        
    except Exception as e:
        print(f"处理8bpp文件时出错: {e}")
        return None

def process_tex_file(input_path, output_folder):
    try:
        with open(input_path, 'rb') as file:
            data = file.read()
            
            # 检查文件是否足够大
            if len(data) < 0x25:
                print(f"文件 {input_path} 太小，无法包含有效的色深信息")
                return False
            
            # 从0x24位置读取色深信息
            if os.path.splitext(input_path)[1].lstrip('.') == 'fac':
                image = read_binary_fac_image_8bpp(data)
            else:
                image = read_binary_agi_image_8bpp(data)

            
            if image:
                # 创建输出文件名（保持原文件名，只修改扩展名为.png）
                output_filename = Path(input_path).stem + ".png"
                output_path = os.path.join(output_folder, output_filename)
                image.save(output_path)
                #print(f"成功转换: {input_path} -> {output_path}")
                return True
            else:
                print(f"无法渲染图像: {input_path}")
                return False
                
    except Exception as e:
        print(f"处理文件 {input_path} 时出错: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("使用方法: python script.py <输入文件夹> <输出文件夹>")
        print("示例: python script.py input_folder output_folder")
        sys.exit(1)
    
    input_folder = sys.argv[1]
    output_folder = sys.argv[2]
    
    # 创建输出文件夹（如果不存在）
    os.makedirs(output_folder, exist_ok=True)
    
    print(f"开始处理文件夹: {input_folder}")
    print(f"输出到文件夹: {output_folder}")
    
    # 统计处理结果
    total_files = 0
    success_files = 0
    
    # 遍历输入文件夹中的所有.tex文件
    for filename in os.listdir(input_folder):
        if filename.lower().endswith(('.fac', '.agi')):
            input_path = os.path.join(input_folder, filename)
            if process_tex_file(input_path, output_folder):
                success_files += 1
            total_files += 1
    
    print(f"\n处理完成: 共 {total_files} 个文件, 成功 {success_files} 个, 失败 {total_files - success_files} 个")
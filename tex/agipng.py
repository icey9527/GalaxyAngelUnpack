import struct
from PIL import Image
import sys
import os
from pathlib import Path

def read_header_info(data):
    # 检查文件是否足够大
    if len(data) < 0x1C:
        raise ValueError("文件太小，无法包含有效的宽度和高度信息")
    
    width = struct.unpack('<H', data[0x18:0x1a])[0]
    
    # 从0x18位置读取宽度，4字节小端序
    height = struct.unpack('<H', data[0x1a:0x1C])[0]
    
    return width, height

def read_binary_image_4bpp(data):

    width, height = read_header_info(data)
    palette_offset = struct.unpack('<I', data[0x1C:0x20])[0]

    pixel_data_offset = 48
    pixel_data = data[pixel_data_offset:]
    
    # 调色板起始位置 (RGBA格式，16个颜色)
    palette = []
    for i in range(16):
        offset = palette_offset + i*4  # 假设调色板紧接在尺寸后
        r, g, b, a = data[offset], data[offset+1], data[offset+2], data[offset+3]
        a = min(a * 2 - 1, 255)
        palette.append((r, g, b, a))
    
    
    # 创建RGBA图像
    img = Image.new('RGBA', (width, height))
    pixels = img.load()
    
    # 解码4bpp数据
    for y in range(height):
        for x in range(width):
            pos = y * width + x
            byte_pos = pos // 2
            if byte_pos >= len(pixel_data):
                pixels[x, y] = (0, 0, 0, 0)  # 越界填充透明黑
                continue
                
            byte = pixel_data[byte_pos]
            index = (byte >> (4 * (pos % 2))) & 0x0F
            pixels[x, y] = palette[index]
    
    return img


def read_binary_image_8bpp(data):
    try:
        width, height = read_header_info(data)
        
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
            a = min(a * 2 - 1, 255)
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
        
        rgba_pixels = [palette[pixel] for pixel in pixel_data[:expected_size]]

        img = Image.new('RGBA', (width, height))

        img.putdata(rgba_pixels)
        
        return img
        
    except Exception as e:
        print(f"处理8bpp文件时出错: {e}")
        return None

def read_binary_image_16bpp(data):
    try:
        width, height = read_header_info(data)
        
        # 计算像素数据开始位置
        pixel_data_offset = 0x20
        pixel_data = data[pixel_data_offset:]
        
        # 检查像素数据是否足够
        expected_size = width * height * 2   # 16位色 = 2字节/像素
        if len(pixel_data) < expected_size:
            raise ValueError("像素数据不足，无法填充指定的宽度和高度")
        
        # 创建新图像 (24位RGB)
        img = Image.new('RGB', (width, height))
        pixels = img.load()
        
        # 填充像素数据
        for y in range(height):
            for x in range(width):
                # 计算当前像素的位置
                pos = (y * width + x) * 2
                if pos + 2 > len(pixel_data):
                    break
                
                # 读取RGB值
                pixel = struct.unpack('<H', pixel_data[pos:pos+2])[0]
                b = (pixel >> 10) & 0x1F
                g = (pixel >> 5) & 0x1F
                r = pixel & 0x1F
                pixels[x, y] = (r << 3 | r >> 2,  # 等效乘以8.23
                                g << 3 | g >> 2, 
                                b << 3 | b >> 2)
        
        return img
        
    except Exception as e:
        print(f"处理16bpp文件时出错: {e}")
        return None

def read_binary_image_24bpp(data):
    try:
        width, height = read_header_info(data)
        
        # 计算像素数据开始位置
        pixel_data_offset = 0x50
        pixel_data = data[pixel_data_offset:]
        
        # 检查像素数据是否足够
        expected_size = width * height * 3  # 24位色 = 3字节/像素
        if len(pixel_data) < expected_size:
            raise ValueError("像素数据不足，无法填充指定的宽度和高度")
        
        # 创建新图像 (24位RGB)
        img = Image.new('RGB', (width, height))
        pixels = img.load()
        
        # 填充像素数据
        for y in range(height):
            for x in range(width):
                # 计算当前像素的位置
                pos = (y * width + x) * 3
                if pos + 2 >= len(pixel_data):
                    break
                
                # 读取RGB值
                r = pixel_data[pos]
                g = pixel_data[pos + 1]
                b = pixel_data[pos + 2]
                
                pixels[x, y] = (r, g, b)
        
        return img
        
    except Exception as e:
        print(f"处理24bpp文件时出错: {e}")
        return None

def process_tex_file(input_path, output_path):
    try:
        with open(input_path, 'rb') as file:
            data = file.read()
            
            # 检查文件是否足够大
            if len(data) < 0x25:
                print(f"文件 {input_path} 太小，无法包含有效的色深信息")
                return False
            
            # 从0x24位置读取色深信息
            bpp_flag = data[0x2c:0x30].hex() 
            
            if bpp_flag == '44494449':
                pass
                image = read_binary_image_16bpp(data)
            elif bpp_flag == "00300100":
                pass
                image = read_binary_image_24bpp(data)
            elif bpp_flag in ['10001000']:
                pass
                image = read_binary_image_8bpp(data)
            elif bpp_flag in ['00001400',"08000200"]:
                pass
                image = read_binary_image_4bpp(data)
            else:
                print(f"文件 {input_path} 有未知的色深标志: {bpp_flag}")
                return False
            
            if image:
                # 创建输出文件名（保持原文件名，只修改扩展名为.png）
                
                image.save(output_path)
                print(f"成功转换: {input_path} -> {output_path}")
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
    for root, dirs, files in os.walk(input_folder):
        for filename in files:
            if filename.lower().endswith('.agi'):
                input_path = os.path.join(root, filename)
                rel_path = os.path.relpath(input_path, input_folder)
                output_rel_path = os.path.splitext(rel_path)[0] + ".png"
                output_path = os.path.join(output_folder, output_rel_path)
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                if process_tex_file(input_path, output_path):
                    success_files += 1
                total_files += 1
    
    print(f"\n处理完成: 共 {total_files} 个文件, 成功 {success_files} 个, 失败 {total_files - success_files} 个")

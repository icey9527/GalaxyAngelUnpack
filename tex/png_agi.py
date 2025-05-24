import struct
import sys
import os
from PIL import Image
import numpy as np
import argparse

def compress_alpha(a):
    a = max(0, min(255, a))
    return min(int(round((a + 1) / 2)), 128) if a > 0 else 0


def png_to_8bpp_agi(png_path, agi_path):
    try:
        # --- 1. 加载原始图像并获取信息 ---
        img = Image.open(png_path).convert('RGBA')
        width, height = img.size

        # --- 2. 量化图像为256色 ---
        quantized_img = img.convert('P')
        pil_palette_rgb = quantized_img.getpalette()[:256 * 3]
        palette_indices = np.array(quantized_img)

        # --- 3. 计算每个调色板项的平均Alpha值 ---
        palette_alphas_sum = [0.0] * 256
        palette_alphas_count = [0] * 256
        palette_alphas = [0] * 256
        original_img_array = np.array(img)

        for y in range(height):
            for x in range(width):
                idx = palette_indices[y, x]
                if 0 <= idx < 256:
                    palette_alphas_sum[idx] += original_img_array[y, x, 3]
                    palette_alphas_count[idx] += 1
                    palette_alphas[idx] = original_img_array[y, x, 3]

        # --- 4. 构建AGI格式的RGBA调色板 ---
        agi_palette = bytearray()
        for major_group_start in range(0, 256, 32):  # 每32色一个大组
            major_group = [pil_palette_rgb[i * 3:i * 3 + 3] for i in range(major_group_start, major_group_start + 32)]
            
            # 将大组分成4个小组（每组8色）
            subgroup1 = major_group[0:8]    # 第1小组
            subgroup2 = major_group[8:16]   # 第2小组
            subgroup3 = major_group[16:24]  # 第3小组
            subgroup4 = major_group[24:32]  # 第4小组
            
            # 交换第2和第3小组
            reordered_major_group = subgroup1 + subgroup3 + subgroup2 + subgroup4
            
            for i in range(32):
                r_val = reordered_major_group[i][0]
                g_val = reordered_major_group[i][1]
                b_val = reordered_major_group[i][2]
                if i < 8:
                    original_offset = i
                elif 8 <= i < 16:
                    original_offset = i + 8  # 对应原subgroup3的位置
                elif 16 <= i < 24:
                    original_offset = i - 8  # 对应原subgroup2的位置
                else:
                    original_offset = i
                a_val = palette_alphas[major_group_start + original_offset]
                a_val_compressed = compress_alpha(a_val)

                agi_palette.extend([r_val, g_val, b_val, a_val_compressed])

        # --- 5. 生成8bpp像素数据 ---
        agi_pixels = bytearray()
        for y in range(height):
            for x in range(width):
                idx = palette_indices[y, x]
                agi_pixels.append(idx)

        # --- 6. 构建AGI文件头 ---
        header = bytearray(48)
        header[0x00:0x04] = b'\x20\x00\x00\x00'
        header[0x04:0x06] = b'\x01\x00'
        header[0x06:0x08] = b'\x01\x00'
        header[0x08:0x0C] = struct.pack('<I', 0x30)  # 像素数据偏移量
        header[0x0E] = 0x13  # 固定值?
        header[0x10:0x12] = struct.pack('<H', 4)  # 每像素位数
        header[0x12:0x14] = struct.pack('<H', height)  # 高度
        header[0x18:0x1A] = struct.pack('<H', width)  # 原始宽度
        header[0x1A:0x1C] = struct.pack('<H', height)  # 高度 (重复?)
        palette_offset = 0x30 + len(agi_pixels)
        header[0x1C:0x20] = struct.pack('<I', palette_offset)  # 调色板偏移量
        header[0x24] = 1  # 固定值?
        header[0x2C:0x2E] = struct.pack('<H', 0x10)  # 固定值?
        header[0x2E:0x30] = struct.pack('<H', 0x10)  # 固定值?

        # --- 7. 写入AGI文件 ---
        with open(agi_path, 'wb') as f:
            f.write(header)
            f.write(agi_pixels)
            f.write(agi_palette)

        print(f"转换成功: {png_path} -> {agi_path}")
        print(f"原始尺寸: {width}x{height}, 像素数据大小: {len(agi_pixels)} bytes, 调色板大小: {len(agi_palette)} bytes")

    except FileNotFoundError:
        print(f"错误: 输入文件未找到 '{png_path}'", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"转换过程中发生错误: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='将PNG图像转换为8bpp AGI格式 (PS2特定Alpha压缩), 修复了调色板Alpha计算。')
    parser.add_argument('input_dir', help='输入目录路径（包含PNG文件）')
    parser.add_argument('output_dir', help='输出目录路径（自动创建）')
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)  # 自动创建输出目录（如果不存在）
    
    for filename in os.listdir(args.input_dir):
        if filename.lower().endswith('.png'):
            png_path = os.path.join(args.input_dir, filename)
            agi_path = os.path.join(args.output_dir, os.path.splitext(filename)[0] + '.agi')
            png_to_8bpp_agi(png_path, agi_path)
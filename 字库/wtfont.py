import argparse
from PIL import Image, ImageDraw, ImageFont
import numpy as np

class TileEncoder:
    def __init__(self, endian_big=False, flipx=False, flipy=False):
        self.endian_big = endian_big
        self.flipx = flipx
        self.flipy = flipy

    def _auto_font_size(self, text, font_path, img_size):
        """二分查找优化字体匹配算法"""
        low, high = 1, 100  # 扩大搜索范围
        best_font = ImageFont.load_default()
        
        while low <= high:
            mid = (low + high) // 2
            try:
                font = ImageFont.truetype(font_path, mid)
            except (IOError, OSError):
                continue  # 跳过无效字体大小
                
            dummy_img = Image.new('L', (1, 1))
            draw = ImageDraw.Draw(dummy_img)
            bbox = draw.textbbox((0, 0), text, font)
            w, h = bbox[2]-bbox[0], bbox[3]-bbox[1]
            
            if w <= img_size[0] and h <= img_size[1]:
                best_font = font
                low = mid + 1  # 尝试更大的字号
            else:
                high = mid - 1
                
        return best_font

    def render_text(self, text, font_path='arial.ttf', img_size=(24, 24), scale_factor=10):
        # 高分辨率渲染参数
        hr_size = (img_size[0]*scale_factor, img_size[1]*scale_factor)
        
        # 字体自动匹配
        base_font = self._auto_font_size(text, font_path, img_size)
        hr_font = ImageFont.truetype(font_path, base_font.size*scale_factor)

        # 高分辨率渲染
        hr_img = Image.new('L', hr_size, 0)
        draw = ImageDraw.Draw(hr_img)
        
        # 精确计算文字位置
        bbox = draw.textbbox((0, 0), text, hr_font)
        # 获取字符边界框
        bbox = draw.textbbox((0, 0), text, font=hr_font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        
        # 水平居中
        x = (hr_size[0] - w) // 2 - bbox[0]
        
        # 垂直对齐：区分标点符号和普通字符
        if text in '，。！？；：""''（）【】《》、.,!?;:\'"()[]<>/':
            # 标点符号：底部对齐，留出下方空间
            y = hr_size[1] - h - bbox[1] - 2 * scale_factor
        elif text in '一丶乀乁':
            # 横线类字符：稍微下移，避免太高
            y = (hr_size[1] - h) // 2 - bbox[1] + 2 * scale_factor        
        else:
            # 普通字符：垂直居中
            y = (hr_size[1] - h) // 2 - bbox[1]
        draw.text((x, y), text, 255, font=hr_font)

        # 高质量下采样
        lr_img = hr_img.resize(img_size, Image.Resampling.LANCZOS)
        
        # 像素数据处理
        data = np.array(lr_img)
        data_4bpp = (data // 16).astype(np.uint8)  # 4bpp量化

        # 应用翻转
        if self.flipx:
            data_4bpp = np.flip(data_4bpp, axis=1)
        if self.flipy:
            data_4bpp = np.flip(data_4bpp, axis=0)

        # 向量化数据打包
        pairs = data_4bpp.reshape(-1, 2)
        if not self.endian_big:
            pairs = pairs[:, ::-1]  # 交换字节序
            
        packed = (pairs[:, 0] << 4) | pairs[:, 1]
        return packed.tobytes()

def parse_codetable(filename):
    """更健壮的码表解析"""
    chars = []
    with open(filename, 'r', encoding='utf-16-le',errors='ignore') as f:
        for line in f:
            line = line.strip()
            if '=' in line:
                parts = line.split('=', 1)
                if len(parts) == 2:
                    chars.append(parts[1].strip())
    return chars

def main():
    parser = argparse.ArgumentParser(description="优化版字体写入工具")
    parser.add_argument("input", help="输入文件")
    parser.add_argument("output", help="输出文件")
    parser.add_argument("--font", required=True)
    parser.add_argument("--font-size", type=int, required=True)
    parser.add_argument("--codetable", required=True)
    parser.add_argument("--tile-w", type=int, default=24)
    parser.add_argument("--tile-h", type=int, default=24)
    parser.add_argument("--offset", type=int, required=True)
    parser.add_argument("--max-tiles", type=int)
    parser.add_argument("--endian-big", action="store_true", help="大端字节序")
    parser.add_argument("--flipx", action="store_true", help="水平翻转")
    parser.add_argument("--flipy", action="store_true", help="垂直翻转")
    
    args = parser.parse_args()

    # 初始化编码器
    encoder = TileEncoder(endian_big=args.endian_big, flipx=args.flipx, flipy=args.flipy)
    tile_size = (args.tile_w * args.tile_h) // 2  # 4bpp计算
    print(f"Tile尺寸: {args.tile_w}x{args.tile_h} 4bpp = {tile_size}字节")

    # 文件处理
    with open(args.input, "rb") as f:
        data = bytearray(f.read())
    
    # 计算最大可写入数量
    max_possible = (len(data) - args.offset) // tile_size
    max_tiles = min(args.max_tiles, max_possible) if args.max_tiles else max_possible
    required_size = args.offset + max_tiles * tile_size
    
    # 自动扩展文件
    if len(data) < required_size:
        data += bytes(required_size - len(data))
        print(f"文件已扩展至 {len(data)//1024}KB")

    # 加载字符
    chars = parse_codetable(args.codetable)[:max_tiles]
    print(f"准备写入 {len(chars)} 个字符")

    # 批量写入
    success_count = 0
    for idx, char in enumerate(chars):
        try:
            offset = args.offset + idx * tile_size
            if offset + tile_size > len(data):
                print(f"偏移越界: 0x{offset:X}")
                break

            # 使用TileEncoder直接生成tile数据
            tile_data = encoder.render_text(
                char, 
                font_path=args.font, 
                img_size=(args.tile_w, args.tile_h)
            )
            
            # 写入数据
            data[offset:offset+tile_size] = tile_data
            success_count += 1
        except Exception as e:
            print(f"失败字符 {idx} '{char}': {str(e)}")
        print(f'\r{idx}')

    # 保存文件
    with open(args.output, "wb") as f:
        f.write(data)
    print(f"写入完成，成功率 {success_count}/{len(chars)}")

if __name__ == "__main__":
    main()

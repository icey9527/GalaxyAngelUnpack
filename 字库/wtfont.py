import argparse
from PIL import Image, ImageDraw, ImageFont
import numpy as np

class TileEncoder:
    def __init__(self, endian_big=False, flipx=False, flipy=False):
        self.endian_big = endian_big
        self.flipx = flipx
        self.flipy = flipy

    def _auto_font_size(self, text, font_path, img_size):
        """自动调整字体大小以适应目标尺寸"""
        for size in range(40, 0, -1):
            font = ImageFont.truetype(font_path, size)
            bbox = ImageDraw.Draw(Image.new('L', (1,1))).textbbox((0,0), text, font)
            if (bbox[2]-bbox[0] <= img_size[0] and 
                bbox[3]-bbox[1] <= img_size[1]):
                return font
        return ImageFont.load_default()

    def render_text(self, text, font_path='arial.ttf', img_size=(24,24)):
        # 创建黑白反色画布（黑底白字）
        img = Image.new('L', img_size, 0)
        draw = ImageDraw.Draw(img)
        
        # 自动调整字体大小
        font = self._auto_font_size(text, font_path, img_size)
        
        # 计算文字位置
        bbox = draw.textbbox((0,0), text, font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = (img_size[0] - text_w)/2 - bbox[0]
        y = (img_size[1] - text_h)/2 - bbox[1]
        draw.text((x, y), text, 255, font=font)

        # 转换为numpy数组并量化到4bpp
        data = np.array(img)
        data_4bpp = (data // 16).astype(np.uint8)  # 0-15

        # 应用翻转（编码时处理）
        if self.flipx:
            data_4bpp = np.flip(data_4bpp, axis=1)
        if self.flipy:
            data_4bpp = np.flip(data_4bpp, axis=0)

        # 打包像素数据
        tile_data = bytearray()
        for row in data_4bpp:
            for i in range(0, 24, 2):
                p1, p2 = row[i], row[i+1]
                byte = (p1 << 4 | p2) if self.endian_big else (p2 << 4 | p1)
                tile_data.append(byte)
        
        return bytes(tile_data)

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

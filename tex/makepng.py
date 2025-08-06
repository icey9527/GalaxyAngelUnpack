import skia
import yaml
import os
import sys
import argparse

def hex_to_color4f(hex_color, alpha=1.0):
    """将十六进制颜色转换为Skia Color4f格式"""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 6:
        r = int(hex_color[0:2], 16) / 255.0
        g = int(hex_color[2:4], 16) / 255.0
        b = int(hex_color[4:6], 16) / 255.0
        return skia.Color4f(r, g, b, alpha)
    else:
        raise ValueError(f"无效的十六进制颜色格式: {hex_color}")

def create_text_image(text, output_path, font_path, font_size=24, width=176, height=24, 
                     scale_factor=4, shadow_offset=1, shadow_opacity=128, outline_width=1,
                     shadow_blur=0, sharp_text=False, font_weight=400, text_color="#FFFFFF",
                     outline_color="#000000", shadow_color="#000000"):
    """
    使用Skia创建带阴影的文字图片（可控制锐利程度）
    
    Args:
        text: 要显示的文字
        output_path: 输出图片路径
        font_path: 字体文件路径
        font_size: 字体大小（像素）
        width: 输出图片宽度
        height: 输出图片高度
        scale_factor: 下采样比例（提高清晰度）
        shadow_offset: 阴影偏移距离（像素）
        shadow_opacity: 阴影不透明度 (0-255)
        outline_width: 文字描边宽度（像素）
        shadow_blur: 阴影模糊半径（像素），设为0则不模糊
        sharp_text: 是否使用锐利文字（关闭抗锯齿）
        font_weight: 字体粗细 (100-900)
        text_color: 文字颜色（十六进制，如 #FFFFFF）
        outline_color: 描边颜色（十六进制，如 #000000）
        shadow_color: 阴影颜色（十六进制，如 #000000）
    """
    # 计算放大后的尺寸
    scaled_width = width * scale_factor
    scaled_height = height * scale_factor
    scaled_font_size = font_size * scale_factor
    scaled_shadow = shadow_offset * scale_factor
    scaled_outline = outline_width * scale_factor
    scaled_blur = shadow_blur * scale_factor if shadow_blur > 0 else 0
    
    # 创建 Skia 表面
    surface = skia.Surface(scaled_width, scaled_height)
    canvas = surface.getCanvas()
    
    # 清空画布（透明背景）
    canvas.clear(skia.Color4f(0, 0, 0, 0))
    
    # 加载字体
    typeface = None
    if font_path and os.path.exists(font_path):
        try:
            typeface = skia.Typeface.MakeFromFile(font_path)
            if not typeface:
                print(f"警告：无法加载字体 {font_path}，使用系统默认字体")
                typeface = skia.Typeface()
        except Exception as e:
            print(f"警告：无法加载字体 {font_path}，使用系统默认字体")
            typeface = skia.Typeface()
    else:
        typeface = skia.Typeface()
    
    # 创建字体对象
    font = skia.Font(typeface, scaled_font_size)
    
    # 根据用户选择设置文字渲染模式
    if sharp_text:
        # 锐利模式：关闭抗锯齿，使用别名渲染
        font.setEdging(skia.Font.Edging.kAlias)
        font.setHinting(skia.FontHinting.kFull)  # 使用完整微调来增强锐利度
        font.setSubpixel(False)  # 关闭亚像素定位
    else:
        # 标准抗锯齿模式（不使用亚像素抗锯齿）
        font.setEdging(skia.Font.Edging.kAntiAlias)
        font.setHinting(skia.FontHinting.kFull)
        font.setSubpixel(True)
    
    # 设置字体粗细
    if font_weight != 400:
        # 创建带有指定粗细的字体样式
        font_style = skia.FontStyle(font_weight, skia.FontStyle.kNormal_Width, skia.FontStyle.kUpright_Slant)
        typeface_with_weight = skia.Typeface.MakeFromName(typeface.getFamilyName(), font_style)
        if typeface_with_weight:
            font = skia.Font(typeface_with_weight, scaled_font_size)
            if sharp_text:
                font.setEdging(skia.Font.Edging.kAlias)
                font.setHinting(skia.FontHinting.kFull)
                font.setSubpixel(False)
            else:
                font.setEdging(skia.Font.Edging.kAntiAlias)
                font.setHinting(skia.FontHinting.kFull)
                font.setSubpixel(True)
    
    # 测量文字
    text_blob = skia.TextBlob.MakeFromString(text, font)
    bounds = font.measureText(text)
    
    # 获取文字的实际边界
    metrics = font.getMetrics()
    
    # 计算居中位置
    x = (scaled_width - bounds) / 2
    y = scaled_height / 2 - metrics.fAscent / 2 - metrics.fDescent / 2
    
    # 创建画笔
    paint = skia.Paint()
    # 根据锐利模式设置画笔抗锯齿
    paint.setAntiAlias(not sharp_text)  # 锐利模式时关闭抗锯齿
    paint.setColor(hex_to_color4f(text_color))  # 使用自定义文字颜色
    
    # 使用 Skia 内置的投影滤镜
    if shadow_opacity > 0:
        # 创建投影滤镜
        shadow_color_obj = hex_to_color4f(shadow_color, shadow_opacity / 255.0)
        
        # 使用正确的 API：DropShadow
        drop_shadow = skia.ImageFilters.DropShadow(
            scaled_shadow,  # dx
            scaled_shadow,  # dy
            scaled_blur,    # sigmaX (0 = 无模糊)
            scaled_blur,    # sigmaY (0 = 无模糊)
            shadow_color_obj.toColor()
        )
        paint.setImageFilter(drop_shadow)
    
    # 如果需要描边，先绘制描边层
    if scaled_outline > 0:
        # 保存当前状态
        canvas.save()
        
        outline_paint = skia.Paint()
        outline_paint.setAntiAlias(not sharp_text)  # 描边也根据锐利模式设置
        outline_paint.setColor(hex_to_color4f(outline_color))  # 使用自定义描边颜色
        outline_paint.setStyle(skia.Paint.kStroke_Style)
        outline_paint.setStrokeWidth(scaled_outline * 2)
        
        # 锐利模式时使用直角连接和端点
        if sharp_text:
            outline_paint.setStrokeJoin(skia.Paint.kMiter_Join)
            outline_paint.setStrokeCap(skia.Paint.kSquare_Cap)
        else:
            outline_paint.setStrokeJoin(skia.Paint.kRound_Join)
            outline_paint.setStrokeCap(skia.Paint.kRound_Cap)
        
        # 如果有阴影，描边也要有阴影
        if shadow_opacity > 0 and paint.getImageFilter():
            outline_paint.setImageFilter(paint.getImageFilter())
        
        canvas.drawTextBlob(text_blob, x, y, outline_paint)
        canvas.restore()
    
    # 绘制主文字（带阴影效果）
    canvas.drawTextBlob(text_blob, x, y, paint)
    
    # 获取图像数据
    image = surface.makeImageSnapshot()
    
    # 如果需要下采样，创建一个新的小尺寸表面
    if scale_factor > 1:
        small_surface = skia.Surface(width, height)
        small_canvas = small_surface.getCanvas()
        
        # 根据锐利模式选择不同的采样方式
        if sharp_text:
            # 锐利模式：使用最近邻采样，保持锐利边缘
            sampling = skia.SamplingOptions(skia.FilterMode.kNearest)
        else:
            # 标准模式：使用线性采样
            sampling = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear)
        
        # 绘制缩小的图像
        resize_paint = skia.Paint()
        resize_paint.setAntiAlias(not sharp_text)
        small_canvas.drawImageRect(image, skia.Rect.MakeWH(width, height), sampling, resize_paint)
        
        image = small_surface.makeImageSnapshot()
    
    # 保存为PNG
    image.save(output_path, skia.kPNG)
    print(f"已生成: {output_path}")

def batch_generate_from_yaml(yaml_file, font_path, font_size=24, 
                           scale_factor=4, shadow_offset=1, shadow_opacity=128, 
                           outline_width=1, shadow_blur=0, sharp_text=False, font_weight=400,
                           text_color="#FFFFFF", outline_color="#000000", shadow_color="#000000",
                           width=176, height=24):
    """
    从YAML文件批量生成图片
    """
    # 检查文件是否存在
    if not os.path.exists(yaml_file):
        print(f"错误：YAML文件不存在: {yaml_file}")
        sys.exit(1)
    
    if font_path and not os.path.exists(font_path):
        print(f"错误：字体文件不存在: {font_path}")
        sys.exit(1)
    
    # 创建输出目录
    yaml_basename = os.path.basename(yaml_file)
    output_dir = os.path.splitext(yaml_basename)[0]
    yaml_dir = os.path.dirname(yaml_file)
    
    if yaml_dir:
        output_dir = os.path.join(yaml_dir, output_dir)
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"创建输出目录: {output_dir}")
    
    # 读取YAML文件
    try:
        with open(yaml_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"错误：无法读取YAML文件 {yaml_file}")
        print(f"错误详情：{e}")
        sys.exit(1)
    
    if not isinstance(data, dict):
        print("错误：YAML文件必须是字典格式，如：filename: 文字")
        sys.exit(1)
    
    print(f"开始生成高清图片（Skia渲染）...")
    print(f"字体: {font_path if font_path else '系统默认'}")
    print(f"字号: {font_size}px")
    print(f"字体粗细: {font_weight}")
    print(f"图片尺寸: {width}x{height}px")
    print(f"文字颜色: {text_color}")
    print(f"描边颜色: {outline_color}")
    print(f"阴影颜色: {shadow_color}")
    print(f"渲染模式: {'锐利模式（无抗锯齿）' if sharp_text else '标准抗锯齿'}")
    print(f"下采样比例: {scale_factor}x")
    print(f"阴影偏移: {shadow_offset}px, 不透明度: {shadow_opacity}/255")
    if shadow_blur > 0:
        print(f"阴影模糊: {shadow_blur}px")
    else:
        print(f"阴影模糊: 无（清晰阴影）")
    print(f"文字描边: {outline_width}px")
    print(f"输出目录: {output_dir}\n")
    
    # 批量生成图片
    success_count = 0
    for filename, text in data.items():
        output_filename = f"{filename}"
        output_path = os.path.join(output_dir, output_filename)
        try:
            create_text_image(
                text, 
                output_path, 
                font_path, 
                font_size,
                width=width,
                height=height,
                shadow_offset=shadow_offset,
                shadow_opacity=shadow_opacity,
                scale_factor=scale_factor,
                outline_width=outline_width,
                shadow_blur=shadow_blur,
                sharp_text=sharp_text,
                font_weight=font_weight,
                text_color=text_color,
                outline_color=outline_color,
                shadow_color=shadow_color
            )
            success_count += 1
        except Exception as e:
            print(f"生成 {output_filename} 时出错: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n完成！成功生成 {success_count}/{len(data)} 张高清图片")
    print(f"图片保存在: {output_dir}")

def main():
    parser = argparse.ArgumentParser(description='批量生成高清带阴影文字PNG图片（可控制锐利程度）')
    parser.add_argument('yaml_file', help='YAML文件路径')
    parser.add_argument('-f', '--font', required=True, help='字体文件路径')
    parser.add_argument('-s', '--size', type=int, default=24, help='字体大小（像素，默认: 24）')
    parser.add_argument('--scale', type=int, default=4, help='下采样比例（默认: 4）')
    parser.add_argument('--shadow', type=int, default=1, help='阴影偏移距离（像素，默认: 1）')
    parser.add_argument('--opacity', type=int, default=128, help='阴影不透明度 (0-255, 默认: 128)')
    parser.add_argument('--outline', type=int, default=1, help='文字描边宽度（像素，默认: 1）')
    parser.add_argument('--blur', type=int, default=0, help='阴影模糊半径（像素，默认: 0，不模糊）')
    parser.add_argument('--sharp', action='store_true', help='使用锐利模式（关闭抗锯齿）')
    parser.add_argument('--weight', type=int, default=400, help='字体粗细 (100-900, 默认: 400)')
    parser.add_argument('--text-color', default='#FFFFFF', help='文字颜色（十六进制，默认: #FFFFFF）')
    parser.add_argument('--outline-color', default='#000000', help='描边颜色（十六进制，默认: #000000）')
    parser.add_argument('--shadow-color', default='#000000', help='阴影颜色（十六进制，默认: #000000）')
    parser.add_argument('--width', type=int, default=176, help='图片宽度（像素，默认: 176）')
    parser.add_argument('--height', type=int, default=24, help='图片高度（像素，默认: 24）')
    
    args = parser.parse_args()
    
    batch_generate_from_yaml(
        args.yaml_file, 
        args.font, 
        args.size,
        scale_factor=args.scale,
        shadow_offset=args.shadow,
        shadow_opacity=args.opacity,
        outline_width=args.outline,
        shadow_blur=args.blur,
        sharp_text=args.sharp,
        font_weight=args.weight,
        text_color=args.text_color,
        outline_color=args.outline_color,
        shadow_color=args.shadow_color,
        width=args.width,
        height=args.height
    )

if __name__ == "__main__":
    main()
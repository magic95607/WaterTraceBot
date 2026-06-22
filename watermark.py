import io
from PIL import Image, ImageDraw, ImageFont

def add_text_watermark(image_bytes: bytes, text: str, position: str = "tile", opacity: float = 0.3, font_size_ratio: float = 0.04) -> io.BytesIO:
    """
    為圖片加上文字浮水印。
    
    :param image_bytes: 原始圖片的 bytes 數據
    :param text: 浮水印文字
    :param position: 浮水印位置，可選: 'tile' (平鋪), 'center' (置中), 'bottom_right' (右下角)
    :param opacity: 浮水印不透明度 (0.0 到 1.0)
    :param font_size_ratio: 字型大小相對於圖片寬度的比例
    :return: 包含處理後圖片的 io.BytesIO 物件
    """
    # 載入圖片
    image = Image.open(io.BytesIO(image_bytes))
    
    # 記住原始格式
    original_format = image.format or "PNG"
    
    # 轉換成 RGBA 以支援透明度
    if image.mode != "RGBA":
        image = image.convert("RGBA")
        
    # 建立一個全透明的浮水印圖層
    watermark_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(watermark_layer)
    
    # 根據圖片大小動態計算字型大小
    width, height = image.size
    font_size = max(16, int(width * font_size_ratio))
    
    # 嘗試載入系統內建中文字型，否則載入英文或預設字型
    font = None
    font_paths = [
        "C:\\Windows\\Fonts\\msjh.ttc",  # 微軟正黑體
        "C:\\Windows\\Fonts\\msjh.ttf",
        "C:\\Windows\\Fonts\\msjhbd.ttc", # 微軟正黑體 粗體
        "C:\\Windows\\Fonts\\arial.ttf",  # Arial
        "C:\\Windows\\Fonts\\simhei.ttf", # 黑體
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", # Linux 文泉驛微米黑
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",   # Linux 文泉驛正黑
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", # Linux Noto CJK Regular
        "/usr/share/fonts/truetype/noto/NotoSansCJK.ttc",         # Linux Noto CJK
    ]
    for path in font_paths:
        try:
            font = ImageFont.truetype(path, font_size)
            break
        except IOError:
            continue
            
    if font is None:
        font = ImageFont.load_default()
        
    # 計算文字寬高
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
    except AttributeError:
        # 舊版 Pillow 相容
        text_w, text_h = draw.textsize(text, font=font)
        
    # 設定文字顏色與不透明度
    alpha = int(255 * opacity)
    text_color = (255, 255, 255, alpha)  # 白色半透明
    
    if position == "center":
        x = (width - text_w) // 2
        y = (height - text_h) // 2
        draw.text((x, y), text, font=font, fill=text_color)
        
    elif position == "bottom_right":
        x = width - text_w - 30
        y = height - text_h - 30
        draw.text((x, y), text, font=font, fill=text_color)
        
    elif position == "tile":
        # 滿版平鋪（防盜圖效果最好）
        # 建立一個單一浮水印的 Tile
        tile_w = text_w + font_size * 6
        tile_h = text_h + font_size * 6
        
        tile = Image.new("RGBA", (tile_w, tile_h), (0, 0, 0, 0))
        tile_draw = ImageDraw.Draw(tile)
        tile_draw.text((tile_w // 2 - text_w // 2, tile_h // 2 - text_h // 2), text, font=font, fill=text_color)
        
        # 將 Tile 旋轉 30 度
        rotated_tile = tile.rotate(30, expand=True, resample=Image.Resampling.BICUBIC)
        rt_w, rt_h = rotated_tile.size
        
        # 平鋪黏貼至浮水印圖層
        for x in range(-rt_w, width + rt_w, rt_w):
            for y in range(-rt_h, height + rt_h, rt_h):
                watermark_layer.alpha_composite(rotated_tile, (x, y))
                
    # 合併浮水印圖層與原圖
    out_image = Image.alpha_composite(image, watermark_layer)
    
    # 轉回原始色彩模式 (若是 JPG，轉回 RGB 以利儲存)
    if original_format == "JPEG" or original_format == "JPG":
        out_image = out_image.convert("RGB")
        
    output = io.BytesIO()
    out_image.save(output, format=original_format)
    output.seek(0)
    return output


def add_image_watermark(image_bytes: bytes, logo_bytes: bytes, position: str = "bottom_right", opacity: float = 0.5, logo_size_ratio: float = 0.15) -> io.BytesIO:
    """
    為圖片加上圖片/Logo 浮水印。
    
    :param image_bytes: 原始圖片的 bytes 數據
    :param logo_bytes: 浮水印 Logo 圖片的 bytes 數據
    :param position: 浮水印位置，可選: 'tile' (平鋪), 'center' (置中), 'bottom_right' (右下角)
    :param opacity: 浮水印不透明度 (0.0 到 1.0)
    :param logo_size_ratio: Logo 寬度相對於圖片寬度的比例
    :return: 包含處理後圖片的 io.BytesIO 物件
    """
    # 載入原圖與 Logo
    image = Image.open(io.BytesIO(image_bytes))
    logo = Image.open(io.BytesIO(logo_bytes))
    
    original_format = image.format or "PNG"
    
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    if logo.mode != "RGBA":
        logo = logo.convert("RGBA")
        
    img_w, img_h = image.size
    logo_w, logo_h = logo.size
    
    # 依比例調整 Logo 尺寸
    target_w = max(32, int(img_w * logo_size_ratio))
    target_h = max(32, int(logo_h * (target_w / logo_w)))
    logo = logo.resize((target_w, target_h), Image.Resampling.LANCZOS)
    
    # 調整 Logo 的不透明度
    if opacity < 1.0:
        r, g, b, a = logo.split()
        a = a.point(lambda p: int(p * opacity))
        logo = Image.merge("RGBA", (r, g, b, a))
        
    watermark_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    
    if position == "center":
        x = (img_w - target_w) // 2
        y = (img_h - target_h) // 2
        watermark_layer.paste(logo, (x, y), logo)
        
    elif position == "bottom_right":
        x = img_w - target_w - 30
        y = img_h - target_h - 30
        watermark_layer.paste(logo, (x, y), logo)
        
    elif position == "tile":
        # 圖片平鋪
        tile_w = target_w + 100
        tile_h = target_h + 100
        
        tile = Image.new("RGBA", (tile_w, tile_h), (0, 0, 0, 0))
        tile.paste(logo, ((tile_w - target_w) // 2, (tile_h - target_h) // 2), logo)
        
        # 稍微旋轉 Logo 平鋪區塊
        rotated_tile = tile.rotate(15, expand=True, resample=Image.Resampling.BICUBIC)
        rt_w, rt_h = rotated_tile.size
        
        for x in range(-rt_w, img_w + rt_w, rt_w):
            for y in range(-rt_h, img_h + rt_h, rt_h):
                watermark_layer.alpha_composite(rotated_tile, (x, y))
                
    # 合併圖層
    out_image = Image.alpha_composite(image, watermark_layer)
    
    if original_format == "JPEG" or original_format == "JPG":
        out_image = out_image.convert("RGB")
        
    output = io.BytesIO()
    out_image.save(output, format=original_format)
    output.seek(0)
    return output

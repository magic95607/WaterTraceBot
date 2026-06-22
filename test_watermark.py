import io
from PIL import Image
import watermark

def test():
    # 1. 建立一張測試用紅色圖片
    print("建立測試圖片中...")
    img = Image.new("RGBA", (800, 600), (200, 50, 50, 255))
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_bytes = img_byte_arr.getvalue()

    # 2. 測試平鋪浮水印
    print("測試 1：套用【平鋪 (Tile)】浮水印...")
    tile_res = watermark.add_text_watermark(img_bytes, "浮水印測試 Tiled Watermark", position="tile", opacity=0.3)
    with open("test_tile.png", "wb") as f:
        f.write(tile_res.read())

    # 3. 測試置中浮水印
    print("測試 2：套用【正中央 (Center)】浮水印...")
    center_res = watermark.add_text_watermark(img_bytes, "機密文件 CONFIDENTIAL", position="center", opacity=0.5)
    with open("test_center.png", "wb") as f:
        f.write(center_res.read())

    # 4. 測試右下角浮水印
    print("測試 3：套用【右下角 (Bottom-Right)】浮水印...")
    br_res = watermark.add_text_watermark(img_bytes, "© 2026 Discord Bot", position="bottom_right", opacity=0.7)
    with open("test_bottom_right.png", "wb") as f:
        f.write(br_res.read())

    print("\n測試完成！已在目錄下生成以下測試圖檔：")
    print("- test_tile.png (平鋪版)")
    print("- test_center.png (置中版)")
    print("- test_bottom_right.png (右下角版)")

if __name__ == "__main__":
    test()

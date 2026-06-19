#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析AI目录下的图片内容
"""

import os
from pathlib import Path
from PIL import Image

def analyze_images():
    """分析图片内容"""
    ai_dir = Path("extract_articles/AI")
    images = sorted([f for f in os.listdir(ai_dir) if f.endswith('.png')])
    
    print(f"找到 {len(images)} 张图片\n")
    
    for i, img_file in enumerate(images, 1):
        img_path = ai_dir / img_file
        try:
            img = Image.open(img_path)
            width, height = img.size
            mode = img.mode
            print(f"{i:2d}. {img_file}")
            print(f"    尺寸: {width}x{height}, 模式: {mode}")
        except Exception as e:
            print(f"{i:2d}. {img_file} - 错误: {e}")

if __name__ == "__main__":
    analyze_images()


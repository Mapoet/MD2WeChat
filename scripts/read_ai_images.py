#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
读取AI目录下的图片内容并提取文字
"""

import os
from pathlib import Path
from PIL import Image
import json

def try_ocr_image(img_path):
    """尝试使用OCR识别图片"""
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(img_path)
        # 转换为RGB模式（tesseract需要RGB）
        if img.mode == 'RGBA':
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            rgb_img.paste(img, mask=img.split()[3])
            img = rgb_img
        text = pytesseract.image_to_string(img, lang='chi_sim+eng')
        return text.strip()
    except Exception as e:
        return f"OCR错误: {e}"

def analyze_all_images():
    """分析所有图片"""
    ai_dir = Path("extract_articles/AI")
    images = sorted([f for f in os.listdir(ai_dir) if f.endswith('.png')])
    
    results = []
    for i, img_file in enumerate(images, 1):
        img_path = ai_dir / img_file
        print(f"处理 {i}/{len(images)}: {img_file}")
        
        # 尝试OCR
        text = try_ocr_image(img_path)
        
        results.append({
            'index': i,
            'filename': img_file,
            'text': text[:500] if text else "无法识别"  # 只保存前500字符
        })
    
    # 保存结果
    output_file = Path("extract_articles/ai_images_content.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n结果已保存到: {output_file}")
    return results

if __name__ == "__main__":
    analyze_all_images()


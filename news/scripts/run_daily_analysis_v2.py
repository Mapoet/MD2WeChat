#!/usr/bin/env python3
"""
卫星新闻深度分析每日运行脚本 V2
使用完整的6步深度分析流水线
"""

import os
import sys
import subprocess
import logging
from datetime import datetime


def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _project_python(project_root: str) -> str:
    """Use venv interpreter when present so deps (e.g. feedparser) match requirements."""
    if os.name == "nt":
        rel = os.path.join("venv", "Scripts", "python.exe")
    else:
        rel = os.path.join("venv", "bin", "python")
    path = os.path.join(project_root, rel)
    return path if os.path.isfile(path) else sys.executable

# 配置日志
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"daily_analysis_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def run_subprocess(argv, description, cwd):
    """运行子进程（列表参数，不使用 shell）并记录日志"""
    logger.info(f"开始: {description}")
    logger.info(f"命令: {' '.join(argv)}")
    
    try:
        result = subprocess.run(
            argv,
            shell=False,
            capture_output=True,
            text=True,
            cwd=cwd
        )
        
        if result.returncode == 0:
            logger.info(f"完成: {description}")
            if result.stdout:
                logger.debug(f"输出: {result.stdout[:500]}...")
        else:
            logger.error(f"失败: {description}")
            logger.error(f"错误代码: {result.returncode}")
            if result.stderr:
                logger.error(f"错误信息: {result.stderr}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"异常: {description} - {str(e)}")
        return False


def main():
    """主函数：运行完整的深度分析流水线"""
    logger.info("=" * 60)
    logger.info("🚀 开始卫星新闻深度分析每日运行")
    logger.info(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    project_root = _project_root()
    py = _project_python(project_root)
    pipeline = os.path.join(project_root, "scripts", "full_analysis_pipeline.py")

    # 步骤1: 运行完整的6步分析流水线
    logger.info("📊 步骤1: 运行完整分析流水线")
    success = run_subprocess(
        [py, pipeline],
        "完整6步分析流水线",
        cwd=project_root,
    )
    
    if not success:
        logger.error("❌ 所有分析流水线均失败")
        return 1
    
    # 记录完成信息
    logger.info("=" * 60)
    logger.info("✅ 卫星新闻深度分析每日运行完成")
    logger.info(f"完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"日志文件: {log_file}")
    logger.info("=" * 60)
    
    # 生成简短的完成摘要
    summary_file = os.path.join(log_dir, f"daily_summary_{datetime.now().strftime('%Y%m%d')}.txt")
    with open(summary_file, 'w') as f:
        f.write(f"卫星新闻深度分析每日运行摘要\n")
        f.write(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"状态: {'成功' if success else '部分成功'}\n")
        f.write(f"日志文件: {log_file}\n")
        f.write(f"网站地址: https://gnss-x.ac.cn/satellite-news/\n")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
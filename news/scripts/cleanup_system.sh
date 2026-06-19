#!/bin/bash

# 卫星新闻系统清理脚本
# 清理30天前的日志和报告文件

set -e

echo "=== 卫星新闻系统清理开始 ==="
echo "当前时间: $(date)"
echo ""

# 设置清理天数
DAYS_OLD=30
CLEAN_DATE=$(date -d "$DAYS_OLD days ago" +%Y%m%d)

echo "清理 $DAYS_OLD 天前（$CLEAN_DATE 之前）的文件"
echo ""

# 1. 清理日志文件
LOG_DIR="/home/ubuntu/works/satellite-news/logs"
echo "清理日志目录: $LOG_DIR"

if [ -d "$LOG_DIR" ]; then
    # 查找并统计要删除的文件
    LOG_FILES_TO_DELETE=$(find "$LOG_DIR" -type f -name "*.log" -mtime +$DAYS_OLD)
    LOG_COUNT=$(echo "$LOG_FILES_TO_DELETE" | wc -l)
    
    echo "找到 $LOG_COUNT 个超过 $DAYS_OLD 天的日志文件"
    
    if [ $LOG_COUNT -gt 0 ]; then
        echo "删除以下日志文件:"
        echo "$LOG_FILES_TO_DELETE"
        echo ""
        
        # 实际删除文件
        find "$LOG_DIR" -type f -name "*.log" -mtime +$DAYS_OLD -delete
        
        echo "日志文件清理完成"
    else
        echo "没有需要清理的日志文件"
    fi
else
    echo "警告: 日志目录不存在: $LOG_DIR"
fi

echo ""

# 2. 清理报告文件
REPORT_DIR="/home/ubuntu/works/satellite-news/reports"
echo "清理报告目录: $REPORT_DIR"

if [ -d "$REPORT_DIR" ]; then
    # 清理daily目录
    DAILY_DIR="$REPORT_DIR/daily"
    if [ -d "$DAILY_DIR" ]; then
        DAILY_FILES_TO_DELETE=$(find "$DAILY_DIR" -type f -name "*.html" -mtime +$DAYS_OLD)
        DAILY_COUNT=$(echo "$DAILY_FILES_TO_DELETE" | wc -l)
        
        echo "找到 $DAILY_COUNT 个超过 $DAYS_OLD 天的daily报告文件"
        
        if [ $DAILY_COUNT -gt 0 ]; then
            echo "删除以下daily报告文件:"
            echo "$DAILY_FILES_TO_DELETE"
            echo ""
            
            find "$DAILY_DIR" -type f -name "*.html" -mtime +$DAYS_OLD -delete
        fi
    fi
    
    # 清理markdown目录
    MARKDOWN_DIR="$REPORT_DIR/markdown"
    if [ -d "$MARKDOWN_DIR" ]; then
        MARKDOWN_FILES_TO_DELETE=$(find "$MARKDOWN_DIR" -type f -name "*.md" -mtime +$DAYS_OLD)
        MARKDOWN_COUNT=$(echo "$MARKDOWN_FILES_TO_DELETE" | wc -l)
        
        echo "找到 $MARKDOWN_COUNT 个超过 $DAYS_OLD 天的markdown报告文件"
        
        if [ $MARKDOWN_COUNT -gt 0 ]; then
            echo "删除以下markdown报告文件:"
            echo "$MARKDOWN_FILES_TO_DELETE"
            echo ""
            
            find "$MARKDOWN_DIR" -type f -name "*.md" -mtime +$DAYS_OLD -delete
        fi
    fi
    
    echo "报告文件清理完成"
else
    echo "警告: 报告目录不存在: $REPORT_DIR"
fi

echo ""
echo "=== 清理完成 ==="
echo "完成时间: $(date)"
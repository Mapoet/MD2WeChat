#!/usr/bin/env bash
#
# 编排「论文周报」全流程：可选自动生成 directions → 地学/遥感/AI 流水线 → GNSS/大气/电离层 流水线。
# 设计用途：cron / systemd timer；请在运行前确保已更新 extract_articles/papers/*7d*.md 与 cursor-agent 可用。
#
# 环境变量（均为可选，见下方默认值）：
#   WEEKLY_DATE              周报日期 YYYY-MM-DD（默认：本机当天）
#   WEEKLY_PYTHON            解释器（默认 python3）
#   WEEKLY_PAPERS_DIR        7d 论文列表目录（默认 extract_articles/papers）
#   WEEKLY_DIRECTIONS_GEO    地学线 directions 文件（yaml/json）
#   WEEKLY_DIRECTIONS_GNSS   GNSS 线 directions 文件
#   WEEKLY_AUTO_SUGGEST      设为 1 时，在跑流水线前用 suggest_direction_indices 覆盖生成上述两个 directions
#   WEEKLY_SUGGEST_STAGING   AUTO_SUGGEST 时临时 analysis 目录（默认 extract_articles/_weekly_suggest_staging）
#   WEEKLY_LOG_DIR           日志目录（默认 extract_articles/_weekly_pipeline_logs；勿放在 _weekly_build 内，流水线成功后会删除该目录）
#   WEEKLY_SKIP_CURSOR       设为 1 时两条流水线均加 --skip-cursor（仅拼装已有 parts）
#   WEEKLY_NO_CHECK          设为 1 时加 --no-check
#   WEEKLY_NO_FORMAT_AUDIT   设为 1 时加 --no-format-audit
#   WEEKLY_COMPARE_GEO       地学线 --compare-md（上期周报路径，可选）
#   WEEKLY_COMPARE_GNSS      GNSS 线 --compare-md（可选）
#
# 命令行：--date YYYY-MM-DD  |  --geo-only  |  --gnss-only  |  --help
#
# Crontab 示例（每周一 06:00；脚本自身会追加写入 weekly-pipeline-日期.log）：
#   0 6 * * 1 cd /path/to/MD2WeChat && WEEKLY_AUTO_SUGGEST=1 ./scripts/run_weekly_pipelines.sh
#
# 仅重新生成 directions、不调用 cursor-agent：
#   WEEKLY_SUGGEST_ONLY=1 WEEKLY_AUTO_SUGGEST=1 ./scripts/run_weekly_pipelines.sh
#
#set -euo pipefail

RUN_GEO=1
RUN_GNSS=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --date)
      WEEKLY_DATE="$2"
      shift 2
      ;;
    --geo-only)
      RUN_GEO=1; RUN_GNSS=0; shift ;;
    --gnss-only)
      RUN_GEO=0; RUN_GNSS=1; shift ;;
    --help|-h)
      sed -n '2,35p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown option: $1 (use --help)" >&2
      exit 1
      ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

WEEKLY_SCRIPT_DIR="${WEEKLY_SCRIPT_DIR:-$REPO_ROOT/.cursor/skills/weekly-research-progress-report/scripts}"
PYTHON="${WEEKLY_PYTHON:-python3}"
PAPERS_DIR="${WEEKLY_PAPERS_DIR:-$REPO_ROOT/extract_articles/papers}"
LOG_DIR="${WEEKLY_LOG_DIR:-$REPO_ROOT/extract_articles/_weekly_pipeline_logs}"
STAGING="${WEEKLY_SUGGEST_STAGING:-$REPO_ROOT/extract_articles/_weekly_suggest_staging}"

DIR_GEO_DEFAULT="$PAPERS_DIR/directions_geoscience_ai.yaml"
DIR_GNSS_DEFAULT="$PAPERS_DIR/directions_gnss_atmo_iono.yaml"
WEEKLY_DIRECTIONS_GEO="${WEEKLY_DIRECTIONS_GEO:-$DIR_GEO_DEFAULT}"
WEEKLY_DIRECTIONS_GNSS="${WEEKLY_DIRECTIONS_GNSS:-$DIR_GNSS_DEFAULT}"

DATA7D="$PAPERS_DIR/data7d.md"
ATMO="$PAPERS_DIR/atmo7d.md"
GNSS="$PAPERS_DIR/gnss7d.md"
GPS="$PAPERS_DIR/gps7d.md"
IONO="$PAPERS_DIR/iono7d.md"

SUGGEST_ONLY="${WEEKLY_SUGGEST_ONLY:-0}"
DATE="${WEEKLY_DATE:-$(date +%F)}"

log() {
  echo "[$(date -Iseconds)] $*"
}

die() {
  log "ERROR: $*"
  exit 1
}

[[ -d "$WEEKLY_SCRIPT_DIR" ]] || die "skill scripts 目录不存在: $WEEKLY_SCRIPT_DIR"

optional_skip=( )
[[ "${WEEKLY_SKIP_CURSOR:-0}" == "1" ]] && optional_skip+=( --skip-cursor )
optional_check=( )
[[ "${WEEKLY_NO_CHECK:-0}" == "1" ]] && optional_check+=( --no-check )
[[ "${WEEKLY_NO_FORMAT_AUDIT:-0}" == "1" ]] && optional_check+=( --no-format-audit )

compare_geo=( )
[[ -n "${WEEKLY_COMPARE_GEO:-}" ]] && [[ -f "${WEEKLY_COMPARE_GEO}" ]] && compare_geo=( --compare-md "$WEEKLY_COMPARE_GEO" )
compare_gnss=( )
[[ -n "${WEEKLY_COMPARE_GNSS:-}" ]] && [[ -f "${WEEKLY_COMPARE_GNSS}" ]] && compare_gnss=( --compare-md "$WEEKLY_COMPARE_GNSS" )

need_data7d=0
need_quad=0
[[ "${WEEKLY_AUTO_SUGGEST:-0}" == "1" ]] && { need_data7d=1; need_quad=1; }
[[ "$RUN_GEO" == "1" ]] && need_data7d=1
[[ "$RUN_GNSS" == "1" ]] && need_quad=1
if [[ "$SUGGEST_ONLY" == "1" ]] && [[ "${WEEKLY_AUTO_SUGGEST:-0}" == "1" ]]; then
  need_data7d=1
  need_quad=1
fi
if [[ "$need_data7d" == "1" ]]; then
  [[ -f "$DATA7D" ]] || die "缺少论文列表: $DATA7D"
fi
if [[ "$need_quad" == "1" ]]; then
  for md in "$ATMO" "$GNSS" "$GPS" "$IONO"; do
    [[ -f "$md" ]] || die "缺少论文列表文件: $md"
  done
fi

mkdir -p "$LOG_DIR" "$STAGING"

log_file="$LOG_DIR/weekly-pipeline-${DATE}.log"
exec >>"$log_file" 2>&1
log "===== 周报流水线开始 repo=$REPO_ROOT date=$DATE log=$log_file ====="

if [[ "${WEEKLY_AUTO_SUGGEST:-0}" == "1" ]]; then
  log "AUTO_SUGGEST: 生成 directions（staging=$STAGING）"
  mkdir -p "$(dirname "$WEEKLY_DIRECTIONS_GEO")" "$(dirname "$WEEKLY_DIRECTIONS_GNSS")"
  analysis_geo="$STAGING/analysis_data7d.json"
  analysis_quad="$STAGING/analysis_atmo_gnss_gps_iono.json"
  "$PYTHON" "$WEEKLY_SCRIPT_DIR/analyze_papers.py" "$DATA7D" -o "$analysis_geo"
  "$PYTHON" "$WEEKLY_SCRIPT_DIR/suggest_direction_indices.py" \
    --analysis "$analysis_geo" --pipeline geoscience_ai -o "$WEEKLY_DIRECTIONS_GEO"
  "$PYTHON" "$WEEKLY_SCRIPT_DIR/analyze_papers.py" "$ATMO" "$GNSS" "$GPS" "$IONO" -o "$analysis_quad"
  "$PYTHON" "$WEEKLY_SCRIPT_DIR/suggest_direction_indices.py" \
    --analysis "$analysis_quad" --pipeline gnss_atmo_iono -o "$WEEKLY_DIRECTIONS_GNSS"
  log "directions 已写入: $WEEKLY_DIRECTIONS_GEO / $WEEKLY_DIRECTIONS_GNSS"
fi

[[ -f "$WEEKLY_DIRECTIONS_GEO" ]] || die "缺少地学线 directions: $WEEKLY_DIRECTIONS_GEO（可设 WEEKLY_AUTO_SUGGEST=1 自动生成）"
[[ -f "$WEEKLY_DIRECTIONS_GNSS" ]] || die "缺少 GNSS 线 directions: $WEEKLY_DIRECTIONS_GNSS"

if [[ "$SUGGEST_ONLY" == "1" ]]; then
  log "WEEKLY_SUGGEST_ONLY=1，跳过 cursor 流水线"
  log "===== 结束（仅 suggest） ====="
  exit 0
fi

command -v cursor-agent >/dev/null 2>&1 || log "WARN: PATH 上未找到 cursor-agent，若未设 WEEKLY_SKIP_CURSOR=1 则可能失败"

if [[ "$RUN_GEO" == "1" ]]; then
  log "运行地学/遥感/AI 流水线 …"
  "$PYTHON" "$WEEKLY_SCRIPT_DIR/run_geoscience_ai_weekly.py" \
    --data7d "$DATA7D" \
    --directions "$WEEKLY_DIRECTIONS_GEO" \
    --date "$DATE" \
    "${compare_geo[@]}" \
    "${optional_skip[@]}" \
    "${optional_check[@]}"
  log "地学线完成: extract_articles/${DATE}-geoscience-ai-weeklys.md"
fi

if [[ "$RUN_GNSS" == "1" ]]; then
  log "运行 GNSS/大气/电离层 流水线 …"
  "$PYTHON" "$WEEKLY_SCRIPT_DIR/run_gnss_atmo_iono_weekly.py" \
    --atmo "$ATMO" \
    --gnss "$GNSS" \
    --gps "$GPS" \
    --iono "$IONO" \
    --directions "$WEEKLY_DIRECTIONS_GNSS" \
    --date "$DATE" \
    "${compare_gnss[@]}" \
    "${optional_skip[@]}" \
    "${optional_check[@]}"
  log "GNSS 线完成: extract_articles/${DATE}-gnss-atmo-iono-weeklys.md"
fi

log "===== 周报流水线成功结束 ====="

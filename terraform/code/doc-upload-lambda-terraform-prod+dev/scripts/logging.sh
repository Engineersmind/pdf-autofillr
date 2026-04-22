#!/usr/bin/env bash
##############################################################################
# scripts/logging.sh
# Logging, metrics, and log inspection for doc-upload-lambda.
#
# Usage:
#   ./scripts/logging.sh tail    <dev|staging|prod>
#   ./scripts/logging.sh errors  <dev|staging|prod> [N]
#   ./scripts/logging.sh metrics <dev|staging|prod>
#   ./scripts/logging.sh s3logs  <dev|staging|prod> <user_id> <session_id> <filled_doc_pdf_id>
#   ./scripts/logging.sh teams   <dev|staging|prod> [N]   # filter Teams failure events
#   ./scripts/logging.sh pipeline <dev|staging|prod> <user_id> <session_id> <filled_doc_pdf_id>
#
# S3 log paths (from logger_utils.py):
#   primary:  s3://{STATIC_BUCKET}/outputs/{user_id}/sessions/{session_id}/{filled_doc_pdf_id}/execution_logs.json
#   prod dup: s3://{PROD_BUCKET}/{env}/{user_type}/{user_id}/sessions/{session_id}/doc_upload/{filled_doc_pdf_id}/execution_logs.json
##############################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TF_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

CMD="${1:-tail}"
ENV="${2:-dev}"
shift 2 || true

cd "${TF_ROOT}"
LOG_GROUP=$(terraform output -raw cloudwatch_log_group 2>/dev/null)
LAMBDA_NAME=$(terraform output -raw lambda_function_name 2>/dev/null)
STATIC_BUCKET=$(terraform output -raw static_bucket_name 2>/dev/null)
PROD_BUCKET=$(terraform output -raw prod_bucket_name 2>/dev/null)
AWS_REGION=$(grep aws_region "environments/${ENV}/terraform.tfvars" | awk -F'"' '{print $2}')

if [[ -z "$LOG_GROUP" ]]; then
  echo "❌  Could not read Terraform outputs. Run constructor.sh first."
  exit 1
fi

case "$CMD" in

  # ── TAIL: live CloudWatch stream ──────────────────────────────────────────
  tail)
    echo ""
    echo "📡  Tailing: ${LOG_GROUP}  (Ctrl+C to stop)"
    echo ""
    aws logs tail "${LOG_GROUP}" \
      --region "${AWS_REGION}" \
      --follow \
      --format short
    ;;

  # ── ERRORS: last N error log events ───────────────────────────────────────
  errors)
    N="${1:-50}"
    echo ""
    echo "🚨  Last ${N} ERROR events"
    echo ""
    aws logs filter-log-events \
      --log-group-name "${LOG_GROUP}" \
      --filter-pattern "ERROR" \
      --region "${AWS_REGION}" \
      --max-items "${N}" \
      --query 'events[*].[timestamp,message]' \
      --output text | \
      while IFS=$'\t' read -r TS MSG; do
        HUMAN=$(date -d "@$((TS / 1000))" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || \
                date -r "$((TS / 1000))" '+%Y-%m-%d %H:%M:%S')
        echo "  [${HUMAN}] ${MSG}"
      done
    echo ""
    ;;

  # ── METRICS: Lambda metrics last hour ────────────────────────────────────
  metrics)
    NOW=$(date -u +%s)
    START=$(date -u -d "@$((NOW - 3600))" '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || \
            date -u -r "$((NOW - 3600))" '+%Y-%m-%dT%H:%M:%SZ')
    END=$(date -u '+%Y-%m-%dT%H:%M:%SZ')

    echo ""
    echo "📊  Lambda Metrics — Last Hour"
    echo "    Function: ${LAMBDA_NAME}"
    echo ""

    stat() {
      aws cloudwatch get-metric-statistics \
        --namespace AWS/Lambda \
        --metric-name "$1" \
        --dimensions Name=FunctionName,Value="${LAMBDA_NAME}" \
        --start-time "$START" --end-time "$END" \
        --period 3600 --statistics "$2" \
        --region "${AWS_REGION}" \
        --query "Datapoints[0].$2" --output text 2>/dev/null || echo "0"
    }

    printf "  %-26s %s\n"    "Invocations:"    "$(stat Invocations Sum)"
    printf "  %-26s %s\n"    "Errors:"         "$(stat Errors Sum)"
    printf "  %-26s %s\n"    "Throttles:"      "$(stat Throttles Sum)"
    printf "  %-26s %sms\n"  "Duration (avg):" "$(stat Duration Average)"
    printf "  %-26s %sms\n"  "Duration (max):" "$(stat Duration Maximum)"
    printf "  %-26s %s\n"    "ConcurrentExec:" "$(stat ConcurrentExecutions Maximum)"
    echo ""
    ;;

  # ── TEAMS: filter Teams failure notifications from logs ────────────────────
  teams)
    N="${1:-20}"
    echo ""
    echo "📣  Last ${N} Teams failure notification events"
    echo ""
    aws logs filter-log-events \
      --log-group-name "${LOG_GROUP}" \
      --filter-pattern "\"[Teams] Failure notification sent\"" \
      --region "${AWS_REGION}" \
      --max-items "${N}" \
      --query 'events[*].[timestamp,message]' \
      --output text | \
      while IFS=$'\t' read -r TS MSG; do
        HUMAN=$(date -d "@$((TS / 1000))" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || \
                date -r "$((TS / 1000))" '+%Y-%m-%d %H:%M:%S')
        echo "  [${HUMAN}] ${MSG}"
      done
    echo ""
    ;;

  # ── S3LOGS: pull execution_logs.json from primary bucket ──────────────────
  # logger_utils.py saves to:
  #   outputs/{user_id}/sessions/{session_id}/{filled_doc_pdf_id}/execution_logs.json
  s3logs)
    USER_ID="${1:-}"
    SESSION_ID="${2:-}"
    PDF_ID="${3:-}"

    if [[ -z "$USER_ID" || -z "$SESSION_ID" || -z "$PDF_ID" ]]; then
      echo "Usage: $0 s3logs <env> <user_id> <session_id> <filled_doc_pdf_id>"
      exit 1
    fi

    KEY="outputs/${USER_ID}/sessions/${SESSION_ID}/${PDF_ID}/execution_logs.json"
    echo ""
    echo "📂  Fetching execution_logs.json"
    echo "    s3://${STATIC_BUCKET}/${KEY}"
    echo ""
    aws s3 cp "s3://${STATIC_BUCKET}/${KEY}" - --region "${AWS_REGION}" | \
      python3 -c "
import json, sys
data = json.load(sys.stdin)
summary = data.get('summary', {})
print('=== SUMMARY ===')
print(f'  Status    : {data.get(\"status\", \"?\")}')
print(f'  Duration  : {data.get(\"total_duration_seconds\", \"?\")}s')
print(f'  API Calls : {summary.get(\"total_api_calls\", 0)}')
print(f'  Errors    : {summary.get(\"total_errors\", 0)}')
print(f'  Success   : {summary.get(\"success\", False)}')
print()
print('=== PROCESS LOG ===')
for e in data.get('process_logs', []):
    print(f'  [{e[\"timestamp\"]}] {e[\"message\"]}')
print()
print('=== ERRORS ===')
for e in data.get('errors', []):
    print(f'  [{e[\"timestamp\"]}] {e[\"message\"]}')
    if 'exception_message' in e:
        print(f'    Exception: {e[\"exception_message\"]}')
"
    echo ""
    ;;

  # ── PIPELINE: full pipeline trace for one session ──────────────────────────
  # Shows both CloudWatch (live) and S3 execution_logs.json summary
  pipeline)
    USER_ID="${1:-}"
    SESSION_ID="${2:-}"
    PDF_ID="${3:-}"

    if [[ -z "$USER_ID" || -z "$SESSION_ID" || -z "$PDF_ID" ]]; then
      echo "Usage: $0 pipeline <env> <user_id> <session_id> <filled_doc_pdf_id>"
      exit 1
    fi

    echo ""
    echo "🔍  Pipeline trace for user=${USER_ID} session=${SESSION_ID} pdf=${PDF_ID}"
    echo ""

    # S3 execution logs
    KEY="outputs/${USER_ID}/sessions/${SESSION_ID}/${PDF_ID}/execution_logs.json"
    echo "── S3 Execution Logs ────────────────────────────────────────────────"
    aws s3 cp "s3://${STATIC_BUCKET}/${KEY}" - --region "${AWS_REGION}" 2>/dev/null | \
      python3 -c "
import json, sys
data = json.load(sys.stdin)
s = data.get('summary', {})
print(f'  Status   : {data.get(\"status\")}')
print(f'  Duration : {data.get(\"total_duration_seconds\")}s')
print(f'  Errors   : {s.get(\"total_errors\", 0)}')
" 2>/dev/null || echo "  (not found — pipeline may still be running)"

    echo ""
    echo "── CloudWatch (session_id filter) ───────────────────────────────────"
    aws logs filter-log-events \
      --log-group-name "${LOG_GROUP}" \
      --filter-pattern "\"${SESSION_ID}\"" \
      --region "${AWS_REGION}" \
      --max-items 100 \
      --query 'events[*].message' \
      --output text 2>/dev/null | head -50 || echo "  (no events found)"
    echo ""
    ;;

  *)
    echo "Unknown command: ${CMD}"
    echo "Usage: $0 <tail|errors|metrics|teams|s3logs|pipeline> <env> [args...]"
    exit 1
    ;;

esac

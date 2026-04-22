#!/usr/bin/env bash
##############################################################################
# scripts/logging.sh
# Live CloudWatch log tailing + Lambda metrics dashboard for rag-lambda.
# Usage:
#   ./scripts/logging.sh tail  <dev|staging|prod>          # live log stream
#   ./scripts/logging.sh metrics <dev|staging|prod>        # last-hour metrics
#   ./scripts/logging.sh errors  <dev|staging|prod> [N]    # last N error events
#   ./scripts/logging.sh s3logs  <dev|staging|prod> <user_id> <session_id> <pdf_id>
##############################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TF_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

CMD="${1:-tail}"
ENV="${2:-dev}"
shift 2 || true

# ── Derive names from Terraform outputs ───────────────────────────────────────

cd "${TF_ROOT}"
LOG_GROUP=$(terraform output -raw aws_cloudwatch_log_group 2>/dev/null)
LAMBDA_NAME=$(terraform output -raw aws_lambda_function_name 2>/dev/null)
AWS_REGION=$(grep aws_region "environments/${ENV}/terraform.tfvars" | awk -F'"' '{print $2}')

if [[ -z "$LOG_GROUP" || -z "$LAMBDA_NAME" ]]; then
  echo "❌  Could not read Terraform outputs. Run constructor.sh first."
  exit 1
fi

# ─────────────────────────────────────────────────────────────────────────────

case "$CMD" in

  # ── TAIL: live log stream ──────────────────────────────────────────────────
  tail)
    echo ""
    echo "📡  Tailing CloudWatch logs..."
    echo "    Log group : ${LOG_GROUP}"
    echo "    Press Ctrl+C to stop."
    echo ""
    aws logs tail "${LOG_GROUP}" \
      --region "${AWS_REGION}" \
      --follow \
      --format short
    ;;

  # ── METRICS: Lambda metrics summary for last hour ──────────────────────────
  metrics)
    NOW=$(date -u +%s)
    ONE_HOUR_AGO=$((NOW - 3600))

    START=$(date -u -d "@${ONE_HOUR_AGO}" '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || \
            date -u -r "${ONE_HOUR_AGO}" '+%Y-%m-%dT%H:%M:%SZ')
    END=$(date -u '+%Y-%m-%dT%H:%M:%SZ')

    echo ""
    echo "📊  Lambda Metrics — Last Hour"
    echo "    Function : ${LAMBDA_NAME}"
    echo "    Period   : ${START} → ${END}"
    echo ""

    fetch_metric() {
      local METRIC="$1"
      local STAT="$2"
      aws cloudwatch get-metric-statistics \
        --namespace AWS/Lambda \
        --metric-name "$METRIC" \
        --dimensions Name=FunctionName,Value="${LAMBDA_NAME}" \
        --start-time "$START" \
        --end-time "$END" \
        --period 3600 \
        --statistics "$STAT" \
        --region "${AWS_REGION}" \
        --query 'Datapoints[0].'$STAT \
        --output text 2>/dev/null || echo "0"
    }

    INVOCATIONS=$(fetch_metric Invocations Sum)
    ERRORS=$(fetch_metric Errors Sum)
    THROTTLES=$(fetch_metric Throttles Sum)
    DURATION_AVG=$(fetch_metric Duration Average)
    DURATION_MAX=$(fetch_metric Duration Maximum)
    COLD_STARTS=$(fetch_metric InitDuration Sum)

    printf "  %-22s %s\n" "Invocations:"    "${INVOCATIONS}"
    printf "  %-22s %s\n" "Errors:"         "${ERRORS}"
    printf "  %-22s %s\n" "Throttles:"      "${THROTTLES}"
    printf "  %-22s %sms\n" "Duration (avg):" "${DURATION_AVG}"
    printf "  %-22s %sms\n" "Duration (max):" "${DURATION_MAX}"
    printf "  %-22s %s\n" "Cold starts:"    "${COLD_STARTS}"
    echo ""
    ;;

  # ── ERRORS: show last N error log events ───────────────────────────────────
  errors)
    N="${1:-50}"
    echo ""
    echo "🚨  Last ${N} ERROR events from ${LOG_GROUP}"
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

  # ── S3LOGS: pull JSONL session logs from S3 ────────────────────────────────
  # Matches logger_service.py path: log/{user_id}/{session_id}/{pdf_id}/*.jsonl
  s3logs)
    USER_ID="${1:-}"
    SESSION_ID="${2:-}"
    PDF_ID="${3:-}"

    if [[ -z "$USER_ID" || -z "$SESSION_ID" || -z "$PDF_ID" ]]; then
      echo "Usage: $0 s3logs <env> <user_id> <session_id> <pdf_id>"
      exit 1
    fi

    RAG_BUCKET=$(terraform output -raw aws_rag_bucket_name 2>/dev/null)
    PREFIX="log/${USER_ID}/${SESSION_ID}/${PDF_ID}/"

    echo ""
    echo "📂  Fetching S3 session logs..."
    echo "    Bucket : s3://${RAG_BUCKET}/${PREFIX}"
    echo ""

    for KEY in $(aws s3 ls "s3://${RAG_BUCKET}/${PREFIX}" --region "${AWS_REGION}" | awk '{print $4}'); do
      echo "  ── ${KEY} ───────────────────────────────"
      aws s3 cp "s3://${RAG_BUCKET}/${PREFIX}${KEY}" - --region "${AWS_REGION}" | \
        jq -r '. | "[" + .timestamp + "] [" + .level + "] " + .message' 2>/dev/null || \
        aws s3 cp "s3://${RAG_BUCKET}/${PREFIX}${KEY}" - --region "${AWS_REGION}"
      echo ""
    done
    ;;

  *)
    echo "Unknown command: ${CMD}"
    echo "Usage: $0 <tail|metrics|errors|s3logs> <env> [args...]"
    exit 1
    ;;

esac

#!/usr/bin/env bash
##############################################################################
# scripts/logging.sh — Prod chatbot lambda log inspection.
#
# Usage:
#   ./scripts/logging.sh tail    [prod]
#   ./scripts/logging.sh errors  [prod] [N]
#   ./scripts/logging.sh metrics [prod]
#   ./scripts/logging.sh session [prod] <user_id> <session_id>
#   ./scripts/logging.sh pdf     [prod] <user_id> <session_id>
#   ./scripts/logging.sh tokens  [prod] <user_id> <session_id>
#   ./scripts/logging.sh teams   [prod] [N]    # Teams is ACTIVE in prod
#   ./scripts/logging.sh auth0   [prod] [N]    # prod Auth0 domain
##############################################################################
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TF_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

CMD="${1:-metrics}"
shift

cd "${TF_ROOT}"
get_out() { terraform output -raw "$1" 2>/dev/null || echo ""; }

LOG_GROUP=$(get_out cloudwatch_log_group)
OUTPUT_BUCKET=$(get_out output_bucket_name)

ENV="${1:-prod}"
shift 2>/dev/null || true
AWS_REGION=$(grep aws_region "environments/${ENV}/terraform.tfvars" | awk -F'"' '{print $2}')

case "$CMD" in

  tail)
    echo "📡  Tailing prod: ${LOG_GROUP}"
    aws logs tail "${LOG_GROUP}" --region "${AWS_REGION}" --follow --format short
    ;;

  errors)
    N="${1:-50}"
    echo "🚨  Last ${N} ERROR events"
    aws logs filter-log-events \
      --log-group-name "${LOG_GROUP}" --filter-pattern "ERROR" \
      --region "${AWS_REGION}" --max-items "${N}" \
      --query 'events[*].[timestamp,message]' --output text | \
      while IFS=$'\t' read -r TS MSG; do
        H=$(date -d "@$((TS/1000))" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || \
            date -r "$((TS/1000))" '+%Y-%m-%d %H:%M:%S')
        echo "  [${H}] ${MSG}"
      done
    ;;

  metrics)
    LAMBDA_NAME=$(get_out lambda_function_name)
    NOW=$(date -u +%s)
    START=$(date -u -d "@$((NOW-3600))" '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || \
            date -u -r "$((NOW-3600))" '+%Y-%m-%dT%H:%M:%SZ')
    END=$(date -u '+%Y-%m-%dT%H:%M:%SZ')

    stat() {
      aws cloudwatch get-metric-statistics \
        --namespace AWS/Lambda --metric-name "$1" \
        --dimensions Name=FunctionName,Value="${LAMBDA_NAME}" \
        --start-time "$START" --end-time "$END" \
        --period 3600 --statistics "$2" --region "${AWS_REGION}" \
        --query "Datapoints[0].$2" --output text 2>/dev/null || echo "0"
    }

    echo ""
    echo "📊  Prod Chatbot Lambda Metrics — Last Hour"
    printf "  %-24s %s\n"    "Invocations:"    "$(stat Invocations Sum)"
    printf "  %-24s %s\n"    "Errors:"         "$(stat Errors Sum)"
    printf "  %-24s %sms\n"  "Duration (avg):" "$(stat Duration Average)"
    printf "  %-24s %sms\n"  "Duration (max):" "$(stat Duration Maximum)"
    printf "  %-24s %s\n"    "Throttles:"      "$(stat Throttles Sum)"
    printf "  %-24s %s\n"    "ConcurrentExec:" "$(stat ConcurrentExecutions Maximum)"
    echo ""
    ;;

  # ── SESSION: session_state.json + log.json ────────────────────────────────
  session)
    USER_ID="${1:-}"; SESSION_ID="${2:-}"
    [[ -z "$USER_ID" || -z "$SESSION_ID" ]] && {
      echo "Usage: $0 session <env> <user_id> <session_id>"; exit 1; }
    echo ""
    echo "── Session State ────────────────────────────────────────────────"
    aws s3 cp "s3://${OUTPUT_BUCKET}/${USER_ID}/sessions/${SESSION_ID}/session_state.json" - \
      --region "${AWS_REGION}" 2>/dev/null | \
      python3 -c "
import json,sys
d=json.load(sys.stdin)
print(f'  State        : {d.get(\"state\")}')
print(f'  Investor Type: {d.get(\"investor_type\")}')
print(f'  Phase        : {d.get(\"phase\",\"N/A\")}')
print(f'  Fields Filled: {len([v for v in d.get(\"live_fill_flat\",{}).values() if v not in (\"\",None,False)])}')
print(f'  PDF Doc ID   : {d.get(\"pdf_doc_id\")}')
print(f'  Env          : {d.get(\"env\")}')
print(f'  Developer ID : {d.get(\"developer_id\",\"none\")}')
" 2>/dev/null || echo "  (not found)"
    echo ""
    ;;

  # ── PDF: calling_filling_logs.json — Steps 1-6 ────────────────────────────
  pdf)
    USER_ID="${1:-}"; SESSION_ID="${2:-}"
    [[ -z "$USER_ID" || -z "$SESSION_ID" ]] && {
      echo "Usage: $0 pdf <env> <user_id> <session_id>"; exit 1; }
    echo ""
    echo "── PDF Filling Workflow ─────────────────────────────────────────"
    aws s3 cp "s3://${OUTPUT_BUCKET}/${USER_ID}/sessions/${SESSION_ID}/calling_filling_logs.json" - \
      --region "${AWS_REGION}" 2>/dev/null | \
      python3 -c "
import json,sys
d=json.load(sys.stdin)
ws=d.get('workflow_state',{})
print(f'  Status    : {d.get(\"status\")}')
print(f'  PDF Doc ID: {d.get(\"pdf_doc_id\")}')
print(f'  Duration  : {d.get(\"total_duration_seconds\",\"?\")}s')
print(f'  Workflow  : step={ws.get(\"current_step\")} status={ws.get(\"status\")} retries={ws.get(\"retry_count\",0)}/{ws.get(\"max_retries\",3)}')
print()
for s in d.get('steps',[]):
    print(f'  Step {s.get(\"step\",\"?\")}: {s.get(\"name\",\"?\")} | {s.get(\"status\")} | {s.get(\"duration_seconds\",\"?\")}s')
" 2>/dev/null || echo "  (not found)"
    echo ""
    ;;

  # ── TOKENS: agent_tokens.json ─────────────────────────────────────────────
  tokens)
    USER_ID="${1:-}"; SESSION_ID="${2:-}"
    [[ -z "$USER_ID" || -z "$SESSION_ID" ]] && {
      echo "Usage: $0 tokens <env> <user_id> <session_id>"; exit 1; }
    echo ""
    echo "── Agent Tokens (gpt-4o-mini cost) ──────────────────────────────"
    aws s3 cp "s3://${OUTPUT_BUCKET}/${USER_ID}/sessions/${SESSION_ID}/agent_tokens.json" - \
      --region "${AWS_REGION}" 2>/dev/null | \
      python3 -c "
import json,sys
d=json.load(sys.stdin)
t=d.get('totals',{})
print(f'  Model     : {d.get(\"model\")}')
print(f'  Calls     : {t.get(\"call_count\")}')
print(f'  Input tok : {t.get(\"input_tokens\")}')
print(f'  Output tok: {t.get(\"output_tokens\")}')
print(f'  Cost USD  : \${t.get(\"cost_usd\",0):.6f}')
" 2>/dev/null || echo "  (not found — prod uses older codebase without token tracking)"
    echo ""
    ;;

  # ── TEAMS: filter Teams notifications (ACTIVE in prod) ────────────────────
  teams)
    N="${1:-20}"
    echo ""
    echo "📣  Last ${N} Teams failure notifications (prod — ACTIVE)"
    aws logs filter-log-events \
      --log-group-name "${LOG_GROUP}" \
      --filter-pattern "\"[Teams] Failure notification sent\"" \
      --region "${AWS_REGION}" --max-items "${N}" \
      --query 'events[*].[timestamp,message]' --output text | \
      while IFS=$'\t' read -r TS MSG; do
        H=$(date -d "@$((TS/1000))" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || \
            date -r "$((TS/1000))" '+%Y-%m-%d %H:%M:%S')
        echo "  [${H}] ${MSG}"
      done
    echo ""
    ;;

  # ── AUTH0: prod Auth0 failures (different domain from dev) ────────────────
  auth0)
    N="${1:-20}"
    echo ""
    echo "🔐  Last ${N} Auth0 failures (prod domain: dev-ust08ro3ukgmtcrx)"
    aws logs filter-log-events \
      --log-group-name "${LOG_GROUP}" \
      --filter-pattern "\"Auth0 token request failed\"" \
      --region "${AWS_REGION}" --max-items "${N}" \
      --query 'events[*].[timestamp,message]' --output text | \
      while IFS=$'\t' read -r TS MSG; do
        H=$(date -d "@$((TS/1000))" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || \
            date -r "$((TS/1000))" '+%Y-%m-%d %H:%M:%S')
        echo "  [${H}] ${MSG}"
      done
    echo ""
    ;;

  *)
    echo "Unknown: ${CMD}"
    echo "Usage: $0 <tail|errors|metrics|session|pdf|tokens|teams|auth0> <env> [args...]"
    exit 1
    ;;
esac

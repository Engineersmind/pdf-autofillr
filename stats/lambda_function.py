# lambda_function.py  (dashboard server — separate from the RAG lambda)
import os

DASHBOARD_KEY  = os.environ.get('DASHBOARD_KEY', '')
RAG_LAMBDA_URL = os.environ.get('RAG_LAMBDA_URL', '')
RAG_API_KEY    = os.environ.get('RAG_API_KEY', '')


def lambda_handler(event, context):

    # ── Auth check via query param ──
    params       = event.get('queryStringParameters') or {}
    provided_key = params.get('key', '')

    if not DASHBOARD_KEY:
        return _resp(500, 'text/plain', 'DASHBOARD_KEY env var not set')

    if provided_key != DASHBOARD_KEY:
        return _resp(401, 'text/html; charset=utf-8', '''
            <html><body style="background:#07090f;color:#f87171;font-family:monospace;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;flex-direction:column;gap:1rem">
            <div style="font-size:3rem">&#9940;</div>
            <div style="font-size:1.2rem">401 Unauthorized</div>
            <div style="font-size:0.8rem;color:#3d4f68">missing or invalid ?key= param</div>
            </body></html>
        ''')

    # ── Serve dashboard ──
    with open('stats.html', 'r') as f:
        html = f.read()

    html = html.replace('id="cfg-url" value=""', f'id="cfg-url" value="{RAG_LAMBDA_URL}"')
    html = html.replace('id="cfg-key" value=""', f'id="cfg-key" value="{RAG_API_KEY}"')

    return _resp(200, 'text/html; charset=utf-8', html)


def _resp(status, content_type, body):
    return {
        'statusCode': status,
        'headers': {
            'Content-Type': content_type,
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-API-Key',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
            'Cache-Control': 'no-cache',
        },
        'body': body
    }

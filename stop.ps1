#!/usr/bin/env pwsh
# ============================================================================
# PDF Autofillr - Stop Server Script (Windows/PowerShell)
# ============================================================================

Write-Host "🛑 Stopping PDF Autofillr Server..." -ForegroundColor Yellow

# Find and kill processes
$processes = Get-Process | Where-Object { 
    $_.ProcessName -eq "python" -and 
    $_.MainWindowTitle -like "*api_server*" 
}

if ($processes) {
    $processes | Stop-Process -Force
    Write-Host "✅ Server stopped" -ForegroundColor Green
} else {
    # Try alternative method
    Get-Process -Name python -ErrorAction SilentlyContinue | 
        Where-Object { (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine -like "*api_server*" } |
        Stop-Process -Force
    
    Write-Host "✅ No server processes found or stopped" -ForegroundColor Green
}

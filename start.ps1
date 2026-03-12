#!/usr/bin/env pwsh
# ============================================================================
# PDF Autofillr - Start Server Script (Windows/PowerShell)
# ============================================================================
# Usage: .\start.ps1

param(
    [switch]$Dev,
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 Starting PDF Autofillr Server..." -ForegroundColor Cyan
Write-Host "==================================`n" -ForegroundColor Cyan

# Check if Ollama is running (if using Ollama)
$envFile = "modules/mapper/.env"
if (Test-Path $envFile) {
    $usingOllama = Select-String -Path $envFile -Pattern "LLM_MODEL=ollama/" -Quiet
    
    if ($usingOllama) {
        Write-Host "🤖 Checking Ollama..." -ForegroundColor Yellow
        try {
            ollama list | Out-Null
            Write-Host "✅ Ollama is running" -ForegroundColor Green
        } catch {
            Write-Host "⚠️  Ollama not found, but your config requires it!" -ForegroundColor Yellow
            Write-Host "   Your .env is configured to use: LLM_MODEL=ollama/..." -ForegroundColor Gray
            Write-Host "   Options:" -ForegroundColor Gray
            Write-Host "   1. Install Ollama now (recommended)" -ForegroundColor White
            Write-Host "   2. Skip and start anyway (server may fail)" -ForegroundColor White
            Write-Host "   3. Cancel and configure a different LLM" -ForegroundColor White
            
            $ollamaChoice = Read-Host "   Enter choice (1-3) [1]"
            if ([string]::IsNullOrWhiteSpace($ollamaChoice)) { $ollamaChoice = "1" }
            
            if ($ollamaChoice -eq "1") {
                Write-Host "📥 Installing Ollama..." -ForegroundColor Yellow
                Write-Host "   Options:" -ForegroundColor Gray
                Write-Host "   a) Install via winget: winget install Ollama.Ollama" -ForegroundColor White
                Write-Host "   b) Download from: https://ollama.ai/download" -ForegroundColor White
                
                if (Get-Command winget -ErrorAction SilentlyContinue) {
                    $installChoice = Read-Host "   Install with winget? (y/n)"
                    if ($installChoice -match "^[Yy]$") {
                        winget install Ollama.Ollama
                        Write-Host "✅ Ollama installed!" -ForegroundColor Green
                        Write-Host "📥 Pulling default model..." -ForegroundColor Yellow
                        ollama pull llama3.1
                        Write-Host "✅ Ready!" -ForegroundColor Green
                    } else {
                        Write-Host "Opening download page..." -ForegroundColor Yellow
                        Start-Process "https://ollama.ai/download"
                        Write-Host "⚠️  Please install Ollama and run .\start.ps1 again" -ForegroundColor Yellow
                        exit 0
                    }
                } else {
                    Write-Host "Opening download page..." -ForegroundColor Yellow
                    Start-Process "https://ollama.ai/download"
                    Write-Host "⚠️  Please install Ollama and run .\start.ps1 again" -ForegroundColor Yellow
                    exit 0
                }
            } elseif ($ollamaChoice -eq "2") {
                Write-Host "⚠️  Continuing without Ollama - server will likely fail!" -ForegroundColor Yellow
                Write-Host "   The server expects Ollama at http://localhost:11434" -ForegroundColor Yellow
            } else {
                Write-Host "To use a different LLM provider:" -ForegroundColor Cyan
                Write-Host "   1. Edit modules/mapper/.env" -ForegroundColor White
                Write-Host "   2. Change LLM_MODEL to:" -ForegroundColor White
                Write-Host "      - gpt-4o (requires OPENAI_API_KEY)" -ForegroundColor White
                Write-Host "      - claude-3-5-sonnet-20241022 (requires ANTHROPIC_API_KEY)" -ForegroundColor White
                Write-Host "   3. Add the corresponding API key" -ForegroundColor White
                Write-Host "   4. Run .\start.ps1 again" -ForegroundColor White
                exit 0
            }
        }
    }
}

# Navigate to mapper module
Set-Location "modules/mapper"

# Start server
Write-Host "`n🌐 Starting API server on http://localhost:$Port..." -ForegroundColor Cyan

if ($Dev) {
    Write-Host "   (Development mode with auto-reload)" -ForegroundColor Gray
    $env:PYTHONPATH = "."
    uvicorn api_server:app --reload --host 0.0.0.0 --port $Port
} else {
    python api_server.py
}

<#
.SYNOPSIS
AgentOps 交互式测试运行面板

.DESCRIPTION
此脚本会自动检查并启动 Docker 依赖（PostgreSQL & Redis），并提供一个交互式终端菜单供开发者选择测试某一个模块，或者进行全阶段集成测试、大模型评估打靶。
#>

$ErrorActionPreference = "Stop"

# 切换到项目根目录
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Definition)
Set-Location $ProjectRoot

# 1. 检查基础设施
Write-Host "`n[系统检查] 正在验证 Docker 基础设施..."
try {
    docker info > $null 2>&1
} catch {
    Write-Error "Docker 未运行，请先启动 Docker Desktop！"
    exit 1
}

Write-Host "启动基础依赖容器 (postgres, redis)..." -ForegroundColor DarkGray
docker-compose up -d postgres redis

Write-Host "等待容器就绪 (3秒)..." -ForegroundColor DarkGray
Start-Sleep -Seconds 3

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONPATH="src"

while ($true) {
    Write-Host "======================================"
    Write-Host "启动 AgentOps 本地测试流水线"
    Write-Host "======================================"
    Write-Host "1. 运行所有单元与集成测试"
    Write-Host "2. 运行 API 路由与接口测试 (test_api.py)"
    Write-Host "3. 运行 Agent 核心逻辑测试 (test_graph_agent.py)"
    Write-Host "4. 运行 Client SDK 连通性测试 (test_client_sdk.py)"
    Write-Host "5. 运行 RAG 知识库大模型评估 (evaluate_rag.py)"
    Write-Host "0. 退出测试面板"
    Write-Host "--------------------------------------"

    $choice = Read-Host "请选择要执行的项 (0-5)"

    $TestResult = $true
    
    # 因为捕捉异常才能获取 Pytest 的非 0 退出码
    $ErrorActionPreference = "Continue"

    switch ($choice) {
        '1' {
            Write-Host "`n>>> 启动全阶段测试..."
            uv run pytest tests/ -v --disable-warnings
            if ($LASTEXITCODE -ne 0) { $TestResult = $false }
        }
        '2' {
            Write-Host "`n>>> 启动 API 测试..."
            uv run pytest tests/test_api.py -v --disable-warnings
            if ($LASTEXITCODE -ne 0) { $TestResult = $false }
        }
        '3' {
            Write-Host "`n>>> 启动 Agent 逻辑测试..."
            uv run pytest tests/test_graph_agent.py -v --disable-warnings
            if ($LASTEXITCODE -ne 0) { $TestResult = $false }
        }
        '4' {
            Write-Host "`n>>> 启动 Client SDK 测试 (需本地后端服务运行在 8080 端口)..."
            uv run pytest tests/test_client_sdk.py -v --disable-warnings
            if ($LASTEXITCODE -ne 0) { $TestResult = $false }
        }
        '5' {
            Write-Host "`n>>> 启动 RAG 评估大模型 (调用 evaluate_rag.py)..."
            uv run python scripts/evaluate_rag.py
            if ($LASTEXITCODE -ne 0) { $TestResult = $false }
        }
        '0' {
            Write-Host "`n退出测试面板。测试依赖的容器仍在后台运行，如需停止请执行: docker-compose down"
            exit 0
        }
        default {
            Write-Host "无效的选择，请重试。"
            continue
        }
    }

    $ErrorActionPreference = "Stop"

    if ($choice -match '^[1-5]$') {
        if ($TestResult) {
            Write-Host "`n测试运行成功"
        } else {
            Write-Host "`n测试运行失败，请检查上方日志。"
        }
        Read-Host "`n按 Enter 键返回主菜单..."
    }
}

# Chatchat Embedding 服务诊断脚本

Write-Host "=== Chatchat Embedding 服务诊断 ===" -ForegroundColor Cyan
Write-Host ""

# 1. 检查 Xinference 服务
Write-Host "[1] 检查 Xinference 服务 (端口 9997)..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:9997/v1/models" -Method GET -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  ✓ Xinference 服务正在运行" -ForegroundColor Green
    $models = $response.Content | ConvertFrom-Json
    if ($models.data) {
        Write-Host "  已加载的模型:" -ForegroundColor Gray
        foreach ($model in $models.data) {
            Write-Host "    - $($model.id) (类型: $($model.object))" -ForegroundColor Gray
        }
    } else {
        Write-Host "  ⚠ 未找到已加载的模型" -ForegroundColor Yellow
        Write-Host "    请运行: xinference launch --model-name bge-m3 --model-type embedding" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ✗ Xinference 服务未运行或无法连接" -ForegroundColor Red
    Write-Host "    错误: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "    请运行: xinference-local --host 127.0.0.1 --port 9997" -ForegroundColor Yellow
}

Write-Host ""

# 2. 检查 Chatchat API
Write-Host "[2] 检查 Chatchat API (端口 7861)..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:7861/docs" -Method GET -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  ✓ Chatchat API 正在运行" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Chatchat API 未运行" -ForegroundColor Red
    Write-Host "    错误: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# 3. 检查配置
Write-Host "[3] 检查配置文件..." -ForegroundColor Yellow
if (Test-Path "model_settings.yaml") {
    Write-Host "  ✓ model_settings.yaml 存在" -ForegroundColor Green
    $config = Get-Content "model_settings.yaml" -Raw
    if ($config -match "DEFAULT_EMBEDDING_MODEL:\s*(\S+)") {
        Write-Host "  默认 Embedding 模型: $($matches[1])" -ForegroundColor Gray
    }
    if ($config -match "api_base_url:\s*(http://[^\s]+)") {
        Write-Host "  API 地址: $($matches[1])" -ForegroundColor Gray
    }
} else {
    Write-Host "  ✗ model_settings.yaml 不存在" -ForegroundColor Red
}

Write-Host ""

# 4. 检查端口占用
Write-Host "[4] 检查端口占用..." -ForegroundColor Yellow
$port9997 = Get-NetTCPConnection -LocalPort 9997 -ErrorAction SilentlyContinue
$port7861 = Get-NetTCPConnection -LocalPort 7861 -ErrorAction SilentlyContinue

if ($port9997) {
    Write-Host "  ✓ 端口 9997 已被占用 (PID: $($port9997.OwningProcess))" -ForegroundColor Green
} else {
    Write-Host "  ✗ 端口 9997 未被占用" -ForegroundColor Red
}

if ($port7861) {
    Write-Host "  ✓ 端口 7861 已被占用 (PID: $($port7861.OwningProcess))" -ForegroundColor Green
} else {
    Write-Host "  ✗ 端口 7861 未被占用" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== 诊断完成 ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "如果 Xinference 服务未运行，请执行以下步骤:" -ForegroundColor Yellow
Write-Host "  1. 在新终端运行: xinference-local --host 127.0.0.1 --port 9997" -ForegroundColor White
Write-Host "  2. 在另一个终端运行: xinference launch --model-name bge-m3 --model-type embedding" -ForegroundColor White
Write-Host "  3. 重新运行此诊断脚本验证" -ForegroundColor White

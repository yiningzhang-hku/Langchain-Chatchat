# 激活虚拟环境脚本
# 在 PowerShell 中运行此脚本

Write-Host "正在激活虚拟环境..." -ForegroundColor Green

# 激活虚拟环境
& .\.venv310\Scripts\Activate.ps1

# 检查是否激活成功
if ($env:VIRTUAL_ENV) {
    Write-Host "✓ 虚拟环境已激活: $env:VIRTUAL_ENV" -ForegroundColor Green
    Write-Host "Python 路径: $(Get-Command python).Source" -ForegroundColor Cyan
} else {
    Write-Host "✗ 虚拟环境激活失败" -ForegroundColor Red
}

<#
Tat ban cong khai: dong link Internet (Tailscale Funnel) va dung ung dung o cong 7860.
Ban phat trien (Docker, cong 5173/8000) khong bi anh huong.
#>
param([int]$Port = 7860)
$ErrorActionPreference = 'Continue'
$Tailscale = (Get-Command tailscale -ErrorAction SilentlyContinue).Source
if (-not $Tailscale) { $Tailscale = Join-Path $env:ProgramFiles 'Tailscale\tailscale.exe' }

if ($Tailscale -and (Test-Path $Tailscale)) {
    Write-Host '-> Dong link Internet' -ForegroundColor Cyan
    & $Tailscale funnel reset
}

$conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($conn) {
    Write-Host "-> Dung ung dung o cong $Port" -ForegroundColor Cyan
    Stop-Process -Id $conn.OwningProcess -Force -Confirm:$false
}

Write-Host 'Da tat ban cong khai.' -ForegroundColor Green

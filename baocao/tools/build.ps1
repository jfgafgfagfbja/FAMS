# Build quyen bao cao va bo slide tren Windows, khong can Perl.
#
#   powershell -ExecutionPolicy Bypass -File baocao\tools\build.ps1
#   powershell -ExecutionPolicy Bypass -File baocao\tools\build.ps1 -ChiBaoCao
#
# Vi sao khong dung latexmk: latexmk la script Perl, ma ban MiKTeX cai bang winget
# khong kem Perl nen se bao "could not find the script engine 'perl'". Script nay
# chay thang xelatex dung so luot can thiet (3 luot + bibtex) nen khong can Perl.
# Tren Overleaf thi khong can script nay, Overleaf tu lo.

param(
    [switch]$ChiBaoCao,   # chi build do-an.pdf
    [switch]$ChiSlide     # chi build slide.pdf
)

$ErrorActionPreference = "Stop"
$BaoCaoDir = Split-Path -Parent $PSScriptRoot
$MiKTeXBin = "$env:LOCALAPPDATA\Programs\MiKTeX\miktex\bin\x64"
if (Test-Path $MiKTeXBin) { $env:PATH = "$MiKTeXBin;$env:PATH" }

if (-not (Get-Command xelatex -ErrorAction SilentlyContinue)) {
    Write-Host "Khong tim thay xelatex. Cai MiKTeX roi chay lai:" -ForegroundColor Red
    Write-Host '  winget install --id MiKTeX.MiKTeX --scope user'
    exit 1
}

Set-Location $BaoCaoDir

function Build-TaiLieu {
    param([string]$Ten, [bool]$CoTaiLieuThamKhao)

    Write-Host "`n=== $Ten ===" -ForegroundColor Cyan
    xelatex -interaction=nonstopmode "$Ten.tex" | Out-Null
    if ($CoTaiLieuThamKhao) { bibtex $Ten | Out-Null }
    xelatex -interaction=nonstopmode "$Ten.tex" | Out-Null
    xelatex -interaction=nonstopmode "$Ten.tex" | Out-Null

    $log = "$Ten.log"
    $soLoi = (Select-String -Path $log -Pattern '^! ' | Measure-Object).Count
    $soTran = (Select-String -Path $log -Pattern 'Overfull \\hbox' | Measure-Object).Count
    $soTrang = (Select-String -Path $log -Pattern 'Output written' | Select-Object -First 1).Line

    if (Test-Path "$Ten.pdf") {
        $kb = [math]::Round((Get-Item "$Ten.pdf").Length / 1KB)
        Write-Host "  $Ten.pdf  ($kb KB)"
    } else {
        Write-Host "  KHONG SINH DUOC PDF" -ForegroundColor Red
    }
    Write-Host "  Loi:     $soLoi"
    Write-Host "  Tran le: $soTran"
    if ($soTrang) { Write-Host "  $($soTrang.Trim())" }
    if ($soLoi -gt 0) {
        Write-Host "  Xem chi tiet: Select-String -Path $log -Pattern '^! ' -Context 0,5" -ForegroundColor Yellow
    }
    return $soLoi
}

$tongLoi = 0
if (-not $ChiSlide)   { $tongLoi += Build-TaiLieu -Ten "do-an" -CoTaiLieuThamKhao $true }
if (-not $ChiBaoCao)  { $tongLoi += Build-TaiLieu -Ten "slide" -CoTaiLieuThamKhao $false }

Write-Host ""
if ($tongLoi -gt 0) { Write-Host "Con $tongLoi loi." -ForegroundColor Red; exit 1 }
Write-Host "Build sach." -ForegroundColor Green
Write-Host "Nho tim chuoi 'CAN BO SUNG' trong PDF truoc khi nop." -ForegroundColor Yellow

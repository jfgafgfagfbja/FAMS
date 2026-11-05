<#
Chay ban cong khai cua FAMS tren chinh may nay, roi mo ra Internet qua Tailscale Funnel.

Ban cong khai tach han khoi ban phat trien:
  - CSDL rieng `fams_public` (mat khau manh); ban phat trien van dung `fams` voi sv123...
  - Chay o cong 7860 va CHI nghe tren 127.0.0.1: nguoi ngoai chi vao duoc qua Tailscale,
    may khac trong mang LAN cung khong goi thang duoc.
  - Giao dien, anh bang chung, khoa ky nam rieng trong thu muc du lieu ($DataDir), nen
    build lai giao dien khi phat trien khong lam thay doi link dang chay.

Chay lai bao nhieu lan cung duoc: phan nao dang chay roi thi bo qua.

    powershell -ExecutionPolicy Bypass -File deploy\tailscale\chay-ban-cong-khai.ps1
    powershell -ExecutionPolicy Bypass -File deploy\tailscale\chay-ban-cong-khai.ps1 -ChiTrenMay
#>
param(
    [string]$DataDir = 'D:\fams-trien-khai',
    [int]$Port = 7860,
    # Chi chay tren may, khong mo ra Internet - dung de thu truoc.
    [switch]$ChiTrenMay
)

# Khong dung 'Stop': PowerShell 5.1 coi moi dong stderr cua lenh ngoai (docker, tailscale)
# la loi va dung giua chung. Tu kiem tra $LASTEXITCODE thay vao do.
$ErrorActionPreference = 'Continue'

$Repo      = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$Python    = Join-Path $Repo 'backend\venv\Scripts\python.exe'

# Tailscale co the cai o bat ky dau (vi du D:\ khi o C: day): uu tien ban tren PATH.
$Tailscale = (Get-Command tailscale -ErrorAction SilentlyContinue).Source
if (-not $Tailscale) { $Tailscale = Join-Path $env:ProgramFiles 'Tailscale\tailscale.exe' }

function Buoc([string]$text) { Write-Host "-> $text" -ForegroundColor Cyan }
function Loi([string]$text)  { Write-Host "LOI: $text" -ForegroundColor Red; exit 1 }

# ---------------------------------------------------------------- 1. Docker
docker info > $null 2>&1
if ($LASTEXITCODE -ne 0) {
    Buoc 'Docker chua chay - dang mo Docker Desktop (mat 1-2 phut)'
    $desktop = Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'
    if (-not (Test-Path $desktop)) { Loi 'Khong tim thay Docker Desktop' }
    Start-Process $desktop
    $up = $false
    for ($i = 0; $i -lt 60; $i++) {
        Start-Sleep -Seconds 3
        docker info > $null 2>&1
        if ($LASTEXITCODE -eq 0) { $up = $true; break }
    }
    if (-not $up) { Loi 'Docker khong khoi dong duoc sau 3 phut' }
}

# ---------------------------------------------------------------- 2. Co so du lieu
Buoc 'Bat co so du lieu'
docker compose -f (Join-Path $Repo 'docker-compose.yml') up -d db > $null 2>&1
$health = ''
for ($i = 0; $i -lt 40; $i++) {
    $health = docker inspect -f '{{.State.Health.Status}}' fams-db-1 2>$null
    if ($health -eq 'healthy') { break }
    Start-Sleep -Seconds 2
}
if ($health -ne 'healthy') { Loi 'Co so du lieu khong san sang' }

$exists = docker exec fams-db-1 psql -U fams -tAc "select 1 from pg_database where datname='fams_public'" 2>$null
if ("$exists".Trim() -ne '1') {
    Loi "Chua co CSDL fams_public. Nap tu $DataDir\fams_public.sql - xem deploy\tailscale\HUONG-DAN.md"
}

# ---------------------------------------------------------------- 3. Ung dung
$listening = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($listening) {
    Buoc "Ban cong khai dang chay san o cong $Port"
    Write-Host '   (Vua sua email.env hoac cap nhat code? Bam tat-fams-cong-khai.cmd truoc roi moi bat lai.)'
} else {
    Buoc 'Khoi dong ban cong khai (nap model nhan dien khuon mat mat khoang 1 phut)'

    $line = Get-Content (Join-Path $Repo 'backend\.env') |
        Where-Object { $_ -match '^DATABASE_URL=' } | Select-Object -First 1
    if (-not $line) { Loi 'Khong doc duoc DATABASE_URL trong backend\.env' }
    # Cung may chu CSDL voi ban phat trien, chi doi ten CSDL (giu nguyen phan ?tham so neu co).
    $env:DATABASE_URL = ($line -replace '^DATABASE_URL=', '') -replace '/[^/?]+(\?.*)?$', '/fams_public$1'

    $keyFile = Join-Path $DataDir 'SECRET_KEY.txt'
    if (-not (Test-Path $keyFile)) { Loi "Thieu $keyFile" }
    $env:SECRET_KEY   = (Get-Content $keyFile -Raw).Trim()
    $env:WEB_DIR      = Join-Path $DataDir 'web'
    $env:EVIDENCE_DIR = Join-Path $DataDir 'evidence'
    New-Item -ItemType Directory -Force $env:EVIDENCE_DIR | Out-Null

    # Link "Xem chi tiet" trong email gui phu huynh tro ve dia chi Tailscale cua may nay.
    if (Test-Path $Tailscale) {
        $dns = (& $Tailscale status --json | ConvertFrom-Json).Self.DNSName
        if ($dns) { $env:APP_PUBLIC_URL = 'https://' + $dns.TrimEnd('.') }
    }

    # Tai khoan Gmail gui email thong bao (tuy chon). Khong co tep nay thi phu huynh van
    # nhan thong bao trong ung dung, chi khong co email. Mau: email.env.example
    $mailFile = Join-Path $DataDir 'email.env'
    $mail = @{}
    if (Test-Path $mailFile) {
        foreach ($l in Get-Content $mailFile) {
            if ($l -match '^\s*([A-Z_]+)\s*=\s*(.*?)\s*$') {
                $value = $Matches[2].Trim('"', "'")
                # Gmail hien mat khau ung dung dang "abcd efgh ijkl mnop" - dau cach chi de doc.
                if ($Matches[1] -eq 'SMTP_PASSWORD') { $value = $value -replace '\s', '' }
                $mail[$Matches[1]] = $value
            }
        }
    }
    # Chua dien mat khau (hoac van de dia chi mau) thi coi nhu chua bat: neu bat, he thong se
    # co gui thu, dang nhap Gmail that bai va danh dau loi tung thu mot.
    $mailReady = $mail['SMTP_HOST'] -and $mail['SMTP_PASSWORD'] -and
                 $mail['SMTP_USER'] -and ($mail['SMTP_USER'] -notmatch 'dia-chi-cua-ban')
    if ($mailReady) {
        foreach ($k in $mail.Keys) { Set-Item -Path "Env:$k" -Value $mail[$k] }
        Buoc "Email thong bao phu huynh: BAT (gui tu $($mail['SMTP_USER']))"
    } elseif (Test-Path $mailFile) {
        Buoc 'Email thong bao phu huynh: TAT (email.env chua dien du dia chi Gmail va mat khau ung dung)'
    } else {
        Buoc 'Email thong bao phu huynh: TAT (chua co email.env) - van co thong bao trong ung dung'
    }

    $log = Join-Path $DataDir 'fams_public.log'
    $err = Join-Path $DataDir 'fams_public.err.log'
    # Start-Process tao tien trinh doc lap: dong cua so PowerShell nay thi app van chay.
    Start-Process -FilePath $Python -WorkingDirectory (Join-Path $Repo 'backend') `
        -WindowStyle Hidden -RedirectStandardOutput $log -RedirectStandardError $err `
        -ArgumentList @('-m', 'uvicorn', 'single_port:app', '--host', '127.0.0.1',
                        '--port', "$Port", '--proxy-headers', '--forwarded-allow-ips', '127.0.0.1')

    $up = $false
    for ($i = 0; $i -lt 60; $i++) {
        Start-Sleep -Seconds 3
        try {
            $r = Invoke-WebRequest "http://127.0.0.1:$Port/api/" -UseBasicParsing -TimeoutSec 3
            if ($r.StatusCode -eq 200) { $up = $true; break }
        } catch { }
    }
    if (-not $up) { Loi "Ban cong khai khong khoi dong duoc - xem nhat ky loi: $err" }
}

if ($ChiTrenMay) {
    Write-Host ''
    Write-Host "Ban cong khai chay tren may: http://127.0.0.1:$Port" -ForegroundColor Green
    Write-Host '(-ChiTrenMay: chua mo ra Internet)'
    exit 0
}

# ---------------------------------------------------------------- 4. Tailscale Funnel
if (-not (Test-Path $Tailscale)) { Loi 'Chua cai Tailscale - xem buoc 1 trong deploy\tailscale\HUONG-DAN.md' }

Buoc 'Mo ra Internet qua Tailscale Funnel'
# --bg: cau hinh duoc Tailscale ghi nho, may khoi dong lai van con. Lan dau neu Funnel
# chua duoc bat cho mang Tailscale cua ban, lenh nay in ra mot duong link de bam duyet.
& $Tailscale funnel --bg $Port
if ($LASTEXITCODE -ne 0) { Loi 'Khong bat duoc Funnel - xem thong bao phia tren' }

$self = (& $Tailscale status --json | ConvertFrom-Json).Self
$url  = 'https://' + $self.DNSName.TrimEnd('.')

# May nay luon vao duoc link qua mang noi bo cua Tailscale, ke ca khi nguoi ngoai khong vao
# duoc - nen phai hoi DNS cong khai (qua HTTPS de Tailscale tren may khong chan giua) moi biet
# dien thoai o ngoai co tim thay ten mien hay khong.
$publicDns = $null
try {
    $answer = Invoke-RestMethod "https://dns.google/resolve?name=$($self.DNSName.TrimEnd('.'))&type=A" -TimeoutSec 10
    $publicDns = @($answer.Answer | Where-Object { $_.type -eq 1 } | ForEach-Object { $_.data })
} catch { }

Write-Host ''
Write-Host '================================================================' -ForegroundColor Green
Write-Host " LINK CONG KHAI: $url" -ForegroundColor Green
Write-Host '================================================================' -ForegroundColor Green
if ($publicDns -and $publicDns.Count -gt 0) {
    Write-Host "Nguoi ngoai vao duoc: DNS cong khai da tro ve $($publicDns -join ', ')" -ForegroundColor Green
} else {
    Write-Host 'CANH BAO: DNS cong khai CHUA co ten mien nay - may tinh nay vao duoc nhung dien thoai' -ForegroundColor Yellow
    Write-Host 'va nguoi ngoai THI CHUA. Thuong mat toi 10 phut sau khi bat. Qua 10 phut van vay thi' -ForegroundColor Yellow
    Write-Host 'bam tat-fams-cong-khai.cmd roi bat lai, cho them 10 phut.' -ForegroundColor Yellow
}
Write-Host 'Link chi song khi may nay bat va dang chay. Tat: tat-fams-cong-khai.cmd'

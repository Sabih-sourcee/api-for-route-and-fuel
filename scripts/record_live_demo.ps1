# Records a live desktop demo:
# CMD starts Django -> browser opens API link -> show JSON -> open map
$ErrorActionPreference = "Stop"
$Root = "C:\Users\PC\Documents\fuel-route-api"
$Demo = Join-Path $Root "demo"
$Ffmpeg = "C:\Users\PC\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin\ffmpeg.exe"
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$OutMp4 = Join-Path $Demo "live-demo.mp4"
$Chrome = @(
  "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
  "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
  "$env:LocalAppData\Google\Chrome\Application\chrome.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

New-Item -ItemType Directory -Force -Path $Demo | Out-Null
if (Test-Path $OutMp4) { Remove-Item $OutMp4 -Force }

# Free port 8000 if something is listening
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue |
  ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 1

Write-Host "Starting desktop capture..."
$ffArgs = @(
  "-y",
  "-f", "gdigrab",
  "-framerate", "12",
  "-i", "desktop",
  "-t", "75",
  "-c:v", "libx264",
  "-pix_fmt", "yuv420p",
  "-preset", "ultrafast",
  "-crf", "28",
  $OutMp4
)
$ff = Start-Process -FilePath $Ffmpeg -ArgumentList $ffArgs -PassThru -WindowStyle Minimized
Start-Sleep -Seconds 2

Write-Host "Opening CMD and starting Django..."
$cmdLine = "cd /d `"$Root`" && title Fuel Route API Server && echo Starting Django server... && `"$Python`" manage.py runserver 127.0.0.1:8000"
Start-Process -FilePath "cmd.exe" -ArgumentList "/k", $cmdLine

# Wait until server responds
$ready = $false
for ($i = 0; $i -lt 40; $i++) {
  try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/v1/route/?start=Chicago,%20IL&finish=Denver,%20CO" -UseBasicParsing -TimeoutSec 5
    if ($r.StatusCode -eq 200) { $ready = $true; break }
  } catch {
    Start-Sleep -Seconds 1
  }
}
if (-not $ready) {
  Write-Host "Server did not become ready in time"
}

$apiUrl = "http://127.0.0.1:8000/api/v1/route/?start=Chicago,%20IL&finish=Denver,%20CO"
Write-Host "Opening API in browser: $apiUrl"
if ($Chrome) {
  Start-Process -FilePath $Chrome -ArgumentList "--new-window", "--window-size=1280,900", "--window-position=80,40", $apiUrl
} else {
  Start-Process $apiUrl
}

Start-Sleep -Seconds 12

# Fetch map URL and open it
try {
  $json = Invoke-RestMethod -Uri $apiUrl -TimeoutSec 60
  $map = $json.map_url
  Write-Host "Opening map: $map"
  if ($Chrome) {
    Start-Process -FilePath $Chrome -ArgumentList "--new-window", "--window-size=1280,900", "--window-position=120,80", $map
  } else {
    Start-Process $map
  }
} catch {
  Write-Host "Could not open map: $_"
}

Start-Sleep -Seconds 18

Write-Host "Waiting for ffmpeg to finish..."
Wait-Process -Id $ff.Id -Timeout 90 -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

if (Test-Path $OutMp4) {
  $size = (Get-Item $OutMp4).Length / 1MB
  Write-Host "DONE: $OutMp4 ($([math]::Round($size,1)) MB)"
} else {
  Write-Host "FAILED: video not created"
}

Remove-Item -LiteralPath "$PSScriptRoot\data" -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -LiteralPath "$PSScriptRoot" -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force
Write-Host "Thunderhead reset complete" -ForegroundColor DarkRed

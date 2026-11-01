param([int]$Port = 8767)
$env:PYTHONPYCACHEPREFIX = Join-Path $PSScriptRoot 'tmp/pycache'
Push-Location $PSScriptRoot
try { python -B server.py --port $Port }
finally { Pop-Location }

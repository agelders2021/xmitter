# 2D sweep: V_IN (top-level exciter amplitude) x GRID (PA bias magnitude).
# PARALLEL version - spawns N ngspice workers concurrently.
# Each cell writes to its own .cir and .dat in $env:TEMP\xmitter_sweep\.
#
# Re-save netlist.cir from xmitter.sch in QUCS before running this script.

$ngspice  = "D:\Program Files\Qucs-S\bin\ngspice_con.exe"
$src      = "C:\Users\AlAnd\QucsWorkspace\xmitter_prj\netlist.cir"
$workdir  = "$env:TEMP\xmitter_sweep"
$throttle = [Math]::Max(2, [Environment]::ProcessorCount - 1)

$tranLine = "tran 5n 600u 590u"

$vin_values  = @(5, 7, 10, 15, 20)
$grid_values = @(20, 25, 30, 35, 40)

# Read base netlist, strip .control block
$base = Get-Content $src -Raw
$base = $base -replace "(?s)\.control.*?\.endc", ""

function Set-LastParam([string]$text, [string]$pname, [string]$pval) {
    $pattern = "\.PARAM\s+$pname\s*=\s*[\d\.]+[a-zA-Z]*"
    $matches = [regex]::Matches($text, $pattern)
    if ($matches.Count -eq 0) { return $text }
    $last = $matches[$matches.Count - 1]
    return $text.Substring(0, $last.Index) + ".PARAM $pname = $pval" + $text.Substring($last.Index + $last.Length)
}

function Set-FirstParam([string]$text, [string]$pname, [string]$pval) {
    $pattern = "\.PARAM\s+$pname\s*=\s*[\d\.]+[a-zA-Z]*"
    return [regex]::Replace($text, $pattern, ".PARAM $pname = $pval", 1)
}

# Prepare work dir (clean prior cells so stale .dat files can't fool us)
if (Test-Path $workdir) { Remove-Item "$workdir\*" -Force -ErrorAction SilentlyContinue }
else { New-Item -ItemType Directory -Path $workdir | Out-Null }

# Build cell list
$cells = @()
foreach ($g in $grid_values) {
    foreach ($v in $vin_values) {
        $cells += [PSCustomObject]@{
            grid = $g; vin = $v
            cir  = "$workdir\cell_g${g}_v${v}.cir"
            dat  = "$workdir\cell_g${g}_v${v}.dat"
        }
    }
}

# Write all .cir files up-front
foreach ($c in $cells) {
    $patched = $base
    $patched = Set-FirstParam $patched "GRID" "$($c.grid)V"
    $patched = Set-LastParam  $patched "V_IN" "$($c.vin)V"
    $datPath = $c.dat -replace '\\','/'
    $patched += @"

.control
$tranLine
wrdata $datPath v(pr1)
exit
.endc
.END
"@
    Set-Content -Path $c.cir -Value $patched -Encoding ASCII
}

Write-Host "Spawning $($cells.Count) cells with throttle=$throttle..." -ForegroundColor Cyan
$t0 = Get-Date

# Throttled fan-out: keep up to $throttle ngspice processes alive at once
$running = @{}
$idx = 0
while ($idx -lt $cells.Count -or $running.Count -gt 0) {
    # Top up workers
    while ($running.Count -lt $throttle -and $idx -lt $cells.Count) {
        $c = $cells[$idx]
        $p = Start-Process -FilePath $ngspice `
                           -ArgumentList "-b", "`"$($c.cir)`"" `
                           -NoNewWindow -PassThru `
                           -RedirectStandardOutput "$($c.cir).log" `
                           -RedirectStandardError  "$($c.cir).err"
        $running[$p.Id] = $c
        $idx++
    }
    # Reap any finished
    Start-Sleep -Milliseconds 200
    $toRemove = @()
    foreach ($procId in $running.Keys) {
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        if (-not $proc -or $proc.HasExited) { $toRemove += $procId }
    }
    foreach ($procId in $toRemove) { $running.Remove($procId) | Out-Null }
}

$elapsed = (Get-Date) - $t0
Write-Host ("All cells done in {0:N1}s. Computing power table..." -f $elapsed.TotalSeconds) -ForegroundColor Cyan

# Aggregate results
function Get-PowerFromDat([string]$dat) {
    if (-not (Test-Path $dat)) { return $null }
    $rows = Get-Content $dat
    $ts = @(); $v = @()
    foreach ($r in $rows) {
        $cols = ($r -split '\s+') | Where-Object { $_ -ne '' }
        if ($cols.Count -ge 2) {
            try { $ts += [double]$cols[0]; $v += [double]$cols[1] } catch {}
        }
    }
    if ($v.Count -lt 3) { return $null }
    $sq = 0.0; $dt_t = 0.0
    for ($i = 1; $i -lt $ts.Count; $i++) {
        $dt = $ts[$i] - $ts[$i-1]
        $sq += (($v[$i]*$v[$i] + $v[$i-1]*$v[$i-1])/2) * $dt
        $dt_t += $dt
    }
    $vrms = [math]::Sqrt($sq / $dt_t)
    return $vrms * $vrms / 450
}

# Header
$hdr = "GRID\V_IN"
foreach ($v in $vin_values) { $hdr += ("`t{0,5}V" -f $v) }
$hdr

foreach ($g in $grid_values) {
    $row = "GRID={0,2}V" -f $g
    foreach ($v in $vin_values) {
        $cell = $cells | Where-Object { $_.grid -eq $g -and $_.vin -eq $v } | Select-Object -First 1
        $p = Get-PowerFromDat $cell.dat
        if ($null -eq $p) { $row += "`t  FAIL" }
        else              { $row += ("`t{0,5:F1}W" -f $p) }
    }
    $row
}

"`nDone. Numbers are output power into the 450 ohm load."
"Elapsed: {0:N1}s, throttle: {1} workers." -f $elapsed.TotalSeconds, $throttle

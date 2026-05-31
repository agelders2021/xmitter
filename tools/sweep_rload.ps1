# 1D sweep: R_load directly across PA output, LPF and ATU bypassed.
# Tests the hypothesis "lower PA load impedance -> more output power" cleanly.
#
# Re-save netlist.cir from xmitter.sch in QUCS before running this.

$ngspice  = "D:\Program Files\Qucs-S\bin\ngspice_con.exe"
$src      = "C:\Users\AlAnd\QucsWorkspace\xmitter_prj\netlist.cir"
$workdir  = "$env:TEMP\xmitter_rload"
$throttle = [Math]::Max(2, [Environment]::ProcessorCount - 1)

$tranLine = "tran 5n 600u 590u"

$r_values = @(100, 200, 300, 450, 600, 1000, 2000, 3600)
$VIN      = "5V"
$GRID     = "40V"

# Read & sanitize base netlist
$base = Get-Content $src -Raw
$base = $base -replace "(?s)\.control.*?\.endc", ""

# Remove XLPF and XATU subcircuit instantiations (they bypass)
$base = $base -replace "(?m)^XLPF\s.*\r?\n", ""
$base = $base -replace "(?m)^XATU\s.*\r?\n", ""

# Set top-level params: GRID (1st occurrence inside PA) and V_IN (LAST occurrence = top-level)
function Set-LastParam([string]$t, [string]$n, [string]$v) {
    $m = [regex]::Matches($t, "\.PARAM\s+$n\s*=\s*[\d\.]+[a-zA-Z]*")
    if ($m.Count -eq 0) { return $t }
    $L = $m[$m.Count-1]
    return $t.Substring(0, $L.Index) + ".PARAM $n = $v" + $t.Substring($L.Index + $L.Length)
}
function Set-FirstParam([string]$t, [string]$n, [string]$v) {
    return [regex]::Replace($t, "\.PARAM\s+$n\s*=\s*[\d\.]+[a-zA-Z]*", ".PARAM $n = $v", 1)
}

$base = Set-FirstParam $base "GRID" $GRID
$base = Set-LastParam  $base "V_IN" $VIN

# Add bridge resistors: short _net0 <-> _net5 and _net1 <-> _net6
# This connects the now-dangling R1/Pr1 (at _net0,_net1) to the PA output (_net5,_net6)
# So R1 effectively becomes the only load on the PA output port.
$bridges = @"

* === LPF/ATU bypass bridges (PA OUT directly to R1/Pr1 nodes) ===
RBRIDGE1 _net5 _net0 1u
RBRIDGE2 _net6 _net1 1u
"@
$base += $bridges

# Prepare work dir
if (Test-Path $workdir) { Remove-Item "$workdir\*" -Force -ErrorAction SilentlyContinue }
else { New-Item -ItemType Directory -Path $workdir | Out-Null }

# Build cells (per-R .cir files)
$cells = @()
foreach ($r in $r_values) {
    $cir = "$workdir\rload_$r.cir"
    $dat = "$workdir\rload_$r.dat"
    # Change the top-level R1 value (R1 _net0 _net1 450 tc1=0.0 tc2=0.0)
    $patched = $base -replace "(?m)^R1\s+_net0\s+_net1\s+\S+", "R1 _net0 _net1 $r"
    $datFwd = $dat -replace '\\','/'
    $patched += @"

.control
$tranLine
wrdata $datFwd v(_net0,_net1)
exit
.endc
.END
"@
    Set-Content -Path $cir -Value $patched -Encoding ASCII
    $cells += [PSCustomObject]@{ r = $r; cir = $cir; dat = $dat }
}

Write-Host "Spawning $($cells.Count) cells with throttle=$throttle..." -ForegroundColor Cyan
$t0 = Get-Date

$running = @{}
$idx = 0
while ($idx -lt $cells.Count -or $running.Count -gt 0) {
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
    Start-Sleep -Milliseconds 200
    $toRemove = @()
    foreach ($procId in $running.Keys) {
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        if (-not $proc -or $proc.HasExited) { $toRemove += $procId }
    }
    foreach ($procId in $toRemove) { $running.Remove($procId) | Out-Null }
}

$elapsed = (Get-Date) - $t0
Write-Host ("All cells done in {0:N1}s." -f $elapsed.TotalSeconds) -ForegroundColor Cyan

# Aggregate
function Get-VrmsFromDat([string]$dat) {
    if (-not (Test-Path $dat)) { return $null }
    $rows = Get-Content $dat
    $ts = @(); $v = @()
    foreach ($r in $rows) {
        $cols = ($r -split '\s+') | Where-Object { $_ -ne '' }
        if ($cols.Count -ge 2) { try { $ts += [double]$cols[0]; $v += [double]$cols[1] } catch {} }
    }
    if ($v.Count -lt 3) { return $null }
    $sq = 0.0; $dt_t = 0.0
    for ($i=1; $i -lt $ts.Count; $i++) {
        $dt = $ts[$i]-$ts[$i-1]
        $sq += (($v[$i]*$v[$i] + $v[$i-1]*$v[$i-1])/2) * $dt
        $dt_t += $dt
    }
    return [math]::Sqrt($sq / $dt_t)
}

"`n  R_load (ohm)    Vrms (V)    Power (W)"
"  ------------    --------    ---------"
foreach ($c in $cells) {
    $vrms = Get-VrmsFromDat $c.dat
    if ($null -eq $vrms) {
        "{0,12}    {1,8}    FAIL" -f $c.r, "----"
    } else {
        $p = $vrms * $vrms / $c.r
        "{0,12}    {1,8:F1}    {2,7:F1}" -f $c.r, $vrms, $p
    }
}

"`nV_IN=$VIN, GRID=$GRID, LPF+ATU bypassed."

# Sweep V_IN through the full xmitter chain and report output power.
# Edits a saved netlist.cir, runs ngspice, computes V(Pr1) RMS, prints table.
#
# Usage: re-save netlist.cir from QUCS first (so this script has the latest),
# then run this script from PowerShell.

$ngspice = "D:\Program Files\Qucs-S\bin\ngspice_con.exe"
$src     = "C:\Users\AlAnd\QucsWorkspace\xmitter_prj\netlist.cir"
$work    = "$env:TEMP\sweep_vin.cir"
$out     = "C:\Users\AlAnd\QucsWorkspace\xmitter_prj\sweep_pr1.dat"

# Settling-friendly: long tran, save only the last ~1 us of steady state.
# Adjust the tran line below if your circuit needs more/less.
$tranLine = "tran 5n 600u 590u"

# Values to sweep
$vin_values = @(0.3, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 7.0, 10.0)

# Base content - strip the existing .control block, will add our own
$base = Get-Content $src -Raw
$base = $base -replace "(?s)\.control.*?\.endc", ""

"V_IN(V)`tV_rms(V)`tP_out(W)`tPr4_pk(V)`tNote"

foreach ($vin in $vin_values) {
    # Replace the .PARAM V_IN line (the top-level one at the end of the file -
    # NOT the one inside the Driver_subcircuit which is now unused after V8/V10 disabled)
    $content = $base -replace "(?m)^\.PARAM V_IN = [\d\.]+V?\s*$", ".PARAM V_IN = $vin"
    # Append our control block
    $content += @"

.control
$tranLine
wrdata $($out -replace '\\','/') v(pr1) v(pr4)
exit
.endc
.END
"@
    Set-Content -Path $work -Value $content -Encoding ASCII

    Remove-Item $out -ErrorAction SilentlyContinue
    $log = & $ngspice -b $work 2>&1
    if (-not (Test-Path $out)) {
        $err = ($log | Select-String -Pattern "(Error|Warning|singular)" | Select-Object -First 2) -join "; "
        "{0,6}`tFAILED`t-`t-`t$err" -f $vin
        continue
    }

    $rows = Get-Content $out
    $ts = @(); $vpr1 = @(); $vpr4 = @()
    foreach ($r in $rows) {
        $cols = ($r -split '\s+') | Where-Object { $_ -ne '' }
        if ($cols.Count -ge 4) {
            $ts += [double]$cols[0]; $vpr1 += [double]$cols[1]; $vpr4 += [double]$cols[3]
        }
    }
    if ($vpr1.Count -lt 3) {
        "{0,6}`tNO DATA`t-`t-" -f $vin
        continue
    }
    # Trapezoidal RMS over the whole saved window (already steady-state per tranLine)
    $sq = 0.0; $dt_t = 0.0
    for ($i = 1; $i -lt $ts.Count; $i++) {
        $dt = $ts[$i] - $ts[$i-1]
        $sq += (($vpr1[$i]*$vpr1[$i] + $vpr1[$i-1]*$vpr1[$i-1])/2) * $dt
        $dt_t += $dt
    }
    $vrms = [math]::Sqrt($sq / $dt_t)
    $power = $vrms * $vrms / 450
    $pr4_pk = [math]::Max(($vpr4 | Measure-Object -Maximum).Maximum, -($vpr4 | Measure-Object -Minimum).Minimum)
    "{0,6}`t{1,7:F2}`t{2,7:F2}`t{3,7:F1}" -f $vin, $vrms, $power, $pr4_pk
}

"`nDone. Re-save netlist.cir from QUCS if you change the schematic and re-run."

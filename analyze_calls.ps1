$bin = [System.IO.File]::ReadAllBytes('C:\Users\Adi\Desktop\work\netstorm\NetStorm RIP\netstorm.exe')
$rng_target = 0xF17B0
# We need to find the VAddr of timeGetTime call.
# Actually, let's just search for E8 calls in a range.

# Function boundary detection is hard, but we can look for calls to RNG in loops.
$rng_calls = @()
for ($i=0; $i -lt 0xFE000; $i++) {
    if ($bin[$i] -eq 0xE8) {
        $rel = [BitConverter]::ToInt32($bin, $i+1)
        if ($i + 5 + $rel -eq $rng_target) {
            $rng_calls += $i
        }
    }
}

foreach ($call in $rng_calls) {
    # Scan backwards to find function start (approx)
    $start = $call
    while ($start -gt 0 -and $bin[$start-1] -ne 0xCC) {
        $start--
    }
    # Scan for other calls in this "function"
    for ($j = $start; $j -lt $call + 1000; $j++) {
        if ($bin[$j] -eq 0xE8) {
             # Potentially timeGetTime call? 
             # Let's see if it calls an import.
        }
    }
}

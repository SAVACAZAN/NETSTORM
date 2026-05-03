$bin = [System.IO.File]::ReadAllBytes('C:\Users\Adi\Desktop\work\netstorm\NetStorm RIP\netstorm.exe')
$counts = @{}
for ($i=0x400; $i -lt 0xFE000; $i++) {
    if ($bin[$i] -eq 0xFF -and $bin[$i+1] -eq 0x15) {
        $addr = [BitConverter]::ToUInt32($bin, $i+2)
        if ($addr -ge 0x5BD000 -and $addr -lt 0x5BF000) {
            $counts[$addr] = $counts[$addr] + 1
        }
    }
}
$counts.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 10

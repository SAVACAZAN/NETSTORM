$bin = [System.IO.File]::ReadAllBytes('C:\Users\Adi\Desktop\work\netstorm\NetStorm RIP\netstorm.exe')
$pattern = [byte[]]@(0xFF, 0x05)
for ($i=0; $i -lt 0xFE000; $i++) {
    if ($bin[$i] -eq 0xFF -and $bin[$i+1] -eq 0x05) {
        $addr = [BitConverter]::ToUInt32($bin, $i+2)
        if ($addr -ge 0x500000 -and $addr -lt 0x600000) {
            Write-Output "Possible tick increment at offset $($i.ToString('X')): INC [$($addr.ToString('X'))]"
        }
    }
}

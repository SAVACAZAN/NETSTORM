$bin = [System.IO.File]::ReadAllBytes('C:\Users\Adi\Desktop\work\netstorm\NetStorm RIP\netstorm.exe')
for ($i=0; $i -lt 0xFE000; $i++) {
    if ($bin[$i] -eq 0xFF -and $bin[$i+1] -eq 0x15) {
        $addr = [BitConverter]::ToUInt32($bin, $i+2)
        if ($addr -eq 0x5BD3E4 -or $addr -eq 0x5BD84C) {
             Write-Output "Call to TranslateMessage at offset $($i.ToString('X'))"
        }
    }
}

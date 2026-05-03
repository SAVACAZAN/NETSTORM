$bin = [System.IO.File]::ReadAllBytes('C:\Users\Adi\Desktop\work\netstorm\NetStorm RIP\netstorm.exe')
for ($i=0; $i -lt 0xFE000; $i++) {
    if ($bin[$i] -eq 0x6A -and $bin[$i+1] -eq 0x01 -and $bin[$i+2] -eq 0xFF -and $bin[$i+3] -eq 0x15) {
         Write-Output "Possible Sleep(1) in loop at offset $($i.ToString('X'))"
    }
}

$bin = [System.IO.File]::ReadAllBytes('C:\Users\Adi\Desktop\work\netstorm\NetStorm RIP\netstorm.exe')
for ($i=0; $i -lt 0xFE000; $i++) {
    if ($bin[$i] -eq 0x8B -and $bin[$i+1] -eq 0x0D -and $bin[$i+2] -eq 0xF4 -and $bin[$i+3] -eq 0x72 -and $bin[$i+4] -eq 0x54 -and $bin[$i+5] -eq 0x00) {
         Write-Output "Access to global state pointer at offset $($i.ToString('X'))"
    }
}
for ($i=0; $i -lt 0xFE000; $i++) {
    if ($bin[$i] -eq 0xA1 -and $bin[$i+1] -eq 0xF4 -and $bin[$i+2] -eq 0x72 -and $bin[$i+3] -eq 0x54 -and $bin[$i+4] -eq 0x54 -and $bin[$i+5] -eq 0x00) {
         # Wait, 54 54? No, A1 is 5 bytes.
    }
}

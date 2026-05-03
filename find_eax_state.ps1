$bin = [System.IO.File]::ReadAllBytes('C:\Users\Adi\Desktop\work\netstorm\NetStorm RIP\netstorm.exe')
for ($i=0; $i -lt 0xFE000; $i++) {
    if ($bin[$i] -eq 0xA1 -and $bin[$i+1] -eq 0xF4 -and $bin[$i+2] -eq 0x72 -and $bin[$i+3] -eq 0x54 -and $bin[$i+4] -eq 0x00) {
         Write-Output "MOV EAX, [5472F4] at offset $($i.ToString('X'))"
    }
}

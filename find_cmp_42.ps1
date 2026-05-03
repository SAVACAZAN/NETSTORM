$bin = [System.IO.File]::ReadAllBytes('C:\Users\Adi\Desktop\work\netstorm\NetStorm RIP\netstorm.exe')
for ($i=0; $i -lt 0xFE000; $i++) {
    if ($bin[$i] -eq 0x83 -and $bin[$i+1] -eq 0xF8 -and ($bin[$i+2] -eq 0x42 -or $bin[$i+2] -eq 0x43)) {
         Write-Output "CMP EAX, 66/67 at offset $($i.ToString('X'))"
    }
}

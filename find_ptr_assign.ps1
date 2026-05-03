$bin = [System.IO.File]::ReadAllBytes('C:\Users\Adi\Desktop\work\netstorm\NetStorm RIP\netstorm.exe')
for ($i=0; $i -lt $bin.Length - 4; $i++) {
    if ($bin[$i] -eq 0x89 -and $bin[$i+1] -eq 0x05 -and $bin[$i+2] -eq 0xF4 -and $bin[$i+3] -eq 0x72 -and $bin[$i+4] -eq 0x54 -and $bin[$i+5] -eq 0x00) {
        Write-Output "Assignment to global pointer at offset $($i.ToString('X'))"
    }
}

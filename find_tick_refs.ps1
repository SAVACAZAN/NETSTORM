$bin = [System.IO.File]::ReadAllBytes('C:\Users\Adi\Desktop\work\netstorm\NetStorm RIP\netstorm.exe')
for ($i=0; $i -lt $bin.Length - 4; $i++) {
    if ($bin[$i] -eq 0x50 -and $bin[$i+1] -eq 0x6E -and $bin[$i+2] -eq 0x54 -and $bin[$i+3] -eq 0x00) {
        Write-Output "Reference to tick counter (0x546E50) at offset $($i.ToString('X'))"
    }
}

$bin = [System.IO.File]::ReadAllBytes('C:\Users\Adi\Desktop\work\netstorm\NetStorm RIP\netstorm.exe')
# Search for the RVA of timeGetTime string in the IAT
# RVA of "timeGetTime" string (with hint) is likely 0x1BEBD6
for ($i=0; $i -lt $bin.Length - 4; $i++) {
    if ($bin[$i] -eq 0xD6 -and $bin[$i+1] -eq 0xEB -and $bin[$i+2] -eq 0x1B -and $bin[$i+3] -eq 0x00) {
        Write-Output "Found reference to timeGetTime Name at offset $($i.ToString('X'))"
    }
}

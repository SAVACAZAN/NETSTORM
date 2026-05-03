$bin = [System.IO.File]::ReadAllBytes('C:\Users\Adi\Desktop\work\netstorm\NetStorm RIP\netstorm.exe')
$idata_vaddr = 0x1BD000
$idata_paddr = 0x147400

# Parse Import Directory
# ... too complex for a quick script ...

# Let's search for "timeGetTime" string and its reference.
$str_off = 0
for ($i=0; $i -lt $bin.Length - 12; $i++) {
    if ($bin[$i] -eq 0x74 -and $bin[$i+1] -eq 0x69 -and $bin[$i+2] -eq 0x6D -and $bin[$i+3] -eq 0x65 -and $bin[$i+4] -eq 0x47 -and $bin[$i+5] -eq 0x65 -and $bin[$i+6] -eq 0x74 -and $bin[$i+7] -eq 0x54 -and $bin[$i+8] -eq 0x69 -and $bin[$i+9] -eq 0x6D -and $bin[$i+10] -eq 0x65) {
        $str_off = $i
        Write-Output "Found 'timeGetTime' string at offset $($i.ToString('X'))"
    }
}

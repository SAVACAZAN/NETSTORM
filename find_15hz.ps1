$bin = [System.IO.File]::ReadAllBytes('C:\Users\Adi\Desktop\work\netstorm\NetStorm RIP\netstorm.exe')
for ($i=0; $i -lt 0xFE000; $i++) {
    if ($bin[$i] -eq 0x66 -or $bin[$i] -eq 0x67) {
        # Check if it's a comparison or push
        if ($i -gt 0 -and ($bin[$i-1] -eq 0x6A -or $bin[$i-1] -eq 0x3D)) {
             Write-Output "Possible 15Hz constant (66/67) at offset $($i.ToString('X'))"
        }
    }
}

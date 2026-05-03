$bin = [System.IO.File]::ReadAllBytes('C:\Users\Adi\Desktop\work\netstorm\NetStorm RIP\netstorm.exe')
for ($i=0; $i -lt $bin.Length - 4; $i++) {
    if ($bin[$i] -eq 0xC3 -and $bin[$i+1] -eq 0x9E -and $bin[$i+2] -eq 0x26 -and $bin[$i+3] -eq 0x00) {
        Write-Output "Found MSVC RNG addend (0x269EC3) at offset $($i.ToString('X'))"
    }
}

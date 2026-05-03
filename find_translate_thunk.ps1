$bin = [System.IO.File]::ReadAllBytes('C:\Users\Adi\Desktop\work\netstorm\NetStorm RIP\netstorm.exe')
for ($i=0; $i -lt $bin.Length - 6; $i++) {
    if ($bin[$i] -eq 0xFF -and $bin[$i+1] -eq 0x25) {
        $addr = [BitConverter]::ToUInt32($bin, $i+2)
        if ($addr -eq 0x5BD3E4 -or $addr -eq 0x5BD84C) {
             Write-Output "Thunk for TranslateMessage at offset $($i.ToString('X'))"
        }
    }
}

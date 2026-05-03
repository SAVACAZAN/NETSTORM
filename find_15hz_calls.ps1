$bin = [System.IO.File]::ReadAllBytes('C:\Users\Adi\Desktop\work\netstorm\NetStorm RIP\netstorm.exe')
$target = 0xF99C0
for ($i=0; $i -lt 0xFE000; $i++) {
    if ($bin[$i] -eq 0xE8) {
        $rel = [BitConverter]::ToInt32($bin, $i+1)
        if ($i + 5 + $rel -eq $target) {
            Write-Output "Call to 15Hz check at offset $($i.ToString('X'))"
        }
    }
}

$bin = [System.IO.File]::ReadAllBytes('C:\Users\Adi\Desktop\work\netstorm\NetStorm RIP\netstorm.exe')
# TranslateMessage Name RVA (approx 0x1BDF1A with hint)
$target = 0x1BDF1A 
for ($i=0; $i -lt $bin.Length - 4; $i++) {
    $val = [BitConverter]::ToUInt32($bin, $i)
    if ($val -ge 0x1BD000 -and $val -lt 0x1BF000) {
        # Check if it points to "TranslateMessage"
        $str_off = $val - 0x1BD000 + 0x147400 + 2
        if ($str_off -lt $bin.Length - 16) {
             $name = [System.Text.Encoding]::ASCII.GetString($bin[$str_off..($str_off+15)])
             if ($name -match "TranslateMessage") {
                  $vaddr = $i - 0x147400 + 0x1BD000 + 0x400000
                  Write-Output "IAT entry for TranslateMessage at VAddr 0x$($vaddr.ToString('X')) (File offset $($i.ToString('X')))"
             }
        }
    }
}

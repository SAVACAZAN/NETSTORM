$bin = [System.IO.File]::ReadAllBytes('C:\Users\Adi\Desktop\work\netstorm\NetStorm RIP\netstorm.exe')
$pattern = "TranslateMessage"
$bytes = [System.Text.Encoding]::ASCII.GetBytes($pattern)
for ($i=0; $i -lt $bin.Length - $bytes.Length; $i++) {
    $match = $true
    for ($j=0; $j -lt $bytes.Length; $j++) {
        if ($bin[$i+$j] -ne $bytes[$j]) { $match = $false; break }
    }
    if ($match) {
        Write-Output "Found '$pattern' at offset $($i.ToString('X'))"
    }
}

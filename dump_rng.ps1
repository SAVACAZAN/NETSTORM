$bin = [System.IO.File]::ReadAllBytes('C:\Users\Adi\Desktop\work\netstorm\NetStorm RIP\netstorm.exe')
$offset = 0xF179D
$count = 128
if ($offset + $count -le $bin.Length) {
    $hex = for ($i=0; $i -lt $count; $i++) { '{0:X2}' -f $bin[$offset+$i] }
    Write-Output ($hex -join ' ')
} else {
    Write-Output "Offset out of bounds"
}

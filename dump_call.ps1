$bin = [System.IO.File]::ReadAllBytes('C:\Users\Adi\Desktop\work\netstorm\NetStorm RIP\netstorm.exe')
$start_offset = 0xF17B0 - 10
$count = 64
$hex = for ($i=0; $i -lt $count; $i++) { '{0:X2}' -f $bin[$start_offset+$i] }
Write-Output ($hex -join ' ')

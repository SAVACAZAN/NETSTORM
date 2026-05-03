$bin = [System.IO.File]::ReadAllBytes('C:\Users\Adi\Desktop\work\netstorm\NetStorm RIP\netstorm.exe')
$offset = 0xF99D0
$count = 256
$hex = for ($i=0; $i -lt $count; $i++) { '{0:X2}' -f $bin[$offset+$i] }
Write-Output ($hex -join ' ')

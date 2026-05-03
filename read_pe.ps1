$bin = [System.IO.File]::ReadAllBytes('C:\Users\Adi\Desktop\work\netstorm\NetStorm RIP\netstorm.exe')
$pe_offset = [BitConverter]::ToUInt32($bin, 0x3C)
$num_sections = [BitConverter]::ToUInt16($bin, $pe_offset + 6)
$optional_header_size = [BitConverter]::ToUInt16($bin, $pe_offset + 20)
$section_header_start = $pe_offset + 24 + $optional_header_size

for ($i=0; $i -lt $num_sections; $i++) {
    $offset = $section_header_start + ($i * 40)
    $name = [System.Text.Encoding]::ASCII.GetString($bin[$offset..($offset+7)]).TrimEnd("`0")
    $vsize = [BitConverter]::ToUInt32($bin, $offset + 8)
    $vaddr = [BitConverter]::ToUInt32($bin, $offset + 12)
    $psize = [BitConverter]::ToUInt32($bin, $offset + 16)
    $paddr = [BitConverter]::ToUInt32($bin, $offset + 20)
    Write-Output "Section $name - VAddr: 0x$($vaddr.ToString('X')) - VSize: 0x$($vsize.ToString('X')) - PAddr: 0x$($paddr.ToString('X')) - PSize: 0x$($psize.ToString('X'))"
}

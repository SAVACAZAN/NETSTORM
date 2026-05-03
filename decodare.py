
import struct
import os

def load_tarc_file(tarc_path, target_name):
    """Extrage un fisier specific din arhiva .tarc"""
    with open(tarc_path, 'rb') as f:
        data = f.read()
    
    if not data.startswith(b"TAFF v0.2\x1a"):
        return None
        
    count = struct.unpack_from("<I", data, 20)[0]
    desc_start = struct.unpack_from("<I", data, 32)[0]
    data_start = struct.unpack_from("<I", data, 40)[0]
    
    pos = desc_start
    for _ in range(count):
        d_off = struct.unpack_from("<I", data, pos)[0]
        d_size = struct.unpack_from("<I", data, pos + 4)[0]
        name_start = pos + 8
        name_end = data.find(b"\x00", name_start)
        name = data[name_start:name_end].decode("ascii", errors="replace")
        
        if name.lower() == target_name.lower() or name.lower().endswith(target_name.lower()):
            abs_off = data_start + d_off
            return data[abs_off : abs_off + d_size]
        
        pos = name_end + 1
    return None

def brute_force():
    tarc_path = r"C:\Users\Adi\Desktop\work\netstorm\NetStorm RIP\netstorm.tarc"
    filename = "\\d\\tutorial1.english"
    
    print(f"--- Incarcare {filename} ---")
    raw_data = load_tarc_file(tarc_path, filename)
    
    if not raw_data:
        print("Eroare: Nu am putut gasi fisierul in arhiva!")
        return

    print(f"Fisier incarcat ({len(raw_data)} octeti). Incepem Brute Force...")
    
    # Cuvinte cheie cautate (daca apar, am gasit cheia)
    targets = [b"the", b"NetStorm", b"Islands", b"Welcome", b"tutorial"]
    
    # 1. Testare Single Byte XOR (0-255)
    print("\n[1] Testare cheie simpla (1 byte)...")
    for key in range(256):
        decoded = bytes([b ^ key for b in raw_data[:200]])
        for target in targets:
            if target.lower() in decoded.lower():
                print(f" >>> POSIBILA CHEIE GASITA (Byte): {hex(key)}")
                print(f" Text: {decoded[:100].decode('ascii', errors='replace')}...")
                break

    # 2. Testare Secventa Titanic (EL^KAHL^@TIBJ)
    print("\n[2] Testare secventa repetitiva 'EL^KAHL^@TIBJ'...")
    # Incercam diverse shiftari ale secventei
    base_key = b"EL^KAHL^@TIBJ"
    for shift in range(len(base_key)):
        shifted_key = base_key[shift:] + base_key[:shift]
        decoded = bytes([raw_data[i] ^ shifted_key[i % len(shifted_key)] for i in range(min(len(raw_data), 200))])
        for target in targets:
            if target.lower() in decoded.lower():
                print(f" >>> POSIBILA CHEIE GASITA (Secventa Shiftata {shift}):")
                print(f" Text: {decoded[:100].decode('ascii', errors='replace')}...")
                break

    # 3. Analiza statistica (ce byte apare cel mai des - probabil e 'spatiu' sau 'e')
    print("\n[3] Analiza frecventa (XOR cu cel mai comun byte)...")
    freq = {}
    for b in raw_data:
        freq[b] = freq.get(b, 0) + 1
    most_common = sorted(freq.items(), key=lambda x: x[1], reverse=True)[0][0]
    
    # In engleza, cel mai comun caracter e spatiul (0x20)
    potential_key = most_common ^ ord(' ')
    print(f" Cel mai comun byte: {hex(most_common)}. Daca acesta e 'spatiu', cheia este: {hex(potential_key)}")
    decoded = bytes([b ^ potential_key for b in raw_data[:100]])
    print(f" Text cu cheia {hex(potential_key)}: {decoded.decode('ascii', errors='replace')}")

if __name__ == "__main__":
    brute_force()

# Rezultate Investigație Criptare

Am reușit să decriptăm fișierele NetStorm.

## Cheia de Criptare
**Cheia:** `mydoghasfleas`
**Format:** 13 caractere ASCII.
**Algoritm:** Repeating XOR.

## Validare
Fișierele care au fost confirmate ca fiind decriptate corect:
- `\d\tutorial1.english` (Text clar cu header-ul `[Header]`)
- `\d\altar.type` (Definiție de unitate începând cu `typename Altar`)
- `d\setup.cfg` (Configurație începând cu magic-ul `mQdsT`)

## Implementare
Am actualizat `src/netstorm/assets/tarc.py` pentru a include decriptarea automată în metoda `.get()`.

## Note RE
Șirul `mydoghasfleas` a fost identificat în `netstorm.exe` folosind `Select-String` (echivalentul `strings` + `grep`). Acesta apare în contextul logicii de gestionare a fișierelor (`BaseFile.cpp`) și pare a fi cheia universală pentru activele de tip text/date ale jocului.

# Plan de Implementare NetStorm-Py

Acest document descrie foaia de parcurs pentru finalizarea reimplementării jocului NetStorm: Islands at War cu fidelitate bit-perfect.

## Faza 1: Validarea Fundației (Reverse Engineering)
Fără date exacte din binarul original (`netstorm.exe`), reimplementarea va diverge rapid.
- **Verificarea RNG:** Confirmarea constantelor MSVC în Ghidra. Dacă RNG-ul nu este identic, simularea va "o lua razna" după câteva secunde.
- **Identificarea Structurii de Stare:** Găsirea adreselor de memorie pentru `RNG_State`, `Tick_Counter` și `Player_Data` pentru a putea folosi `harness/record.py`.
- **Identificarea Funcției de Tick:** Localizarea locului unde jocul procesează logica (cele 15 cadre pe secundă).

## Faza 2: Pipeline-ul de Asset-uri
Jocul trebuie să arate ca originalul înainte de a se comporta ca el.
- **Finalizarea `.tarc`:** Confirmarea formatului de arhivă pentru a accesa restul fișierelor.
- **Decoder-ul de Sprite-uri (`.shp`):** Implementarea algoritmului de decompresie RLE/paletizat folosit de Activision în 1997.
- **Managementul Paletei:** NetStorm folosește palete de 8 biți (256 culori) care se schimbă în funcție de efecte (ciclu zi/noapte, fulgere).

## Faza 3: Motorul de Randare și Loop-ul de Bază
- **Implementarea Timer-ului:** Asigurarea că `engine/timer.py` rulează la fix 15.0 Hz, indiferent de FPS-ul randării (60 FPS).
- **Proiecția Izometrică:** Randarea hărții folosind coordonatele extrase din original.
- **Sistemul de UI:** Recrearea meniurilor și a HUD-ului folosind fonturile bitmap (`.chfnt`).

## Faza 4: Paritatea Comportamentală (Differential Testing)
Aici folosim sistemul de "Differential Testing".
- **Înregistrarea Sesiunilor:** Rulăm jocul original și salvăm fișiere `.nsrec`.
- **Replay & Debug:** Rulăm aceleași input-uri în versiunea Python.
- **Eliminarea Divergențelor:** Dacă la tick-ul 500 RNG-ul diferă, investigăm de ce (ex: o funcție de math care a folosit `float64` în loc de `float32`). Scopul este să avem 100% paritate pe sesiuni de 10 minute.

## Faza 5: Logica de Joc (Mecanici)
- **Unități și Clădiri:** Implementarea regulilor de construcție (poduri, temple, unități de atac).
- **Pathfinding:** Replicarea exactă a modului în care unitățile se mișcă.
- **AI:** Portarea logicii de decizie pentru inamicii computerizați.

## Faza 6: Networking și Polish
- **Protocolul de Rețea:** Replicarea arhitecturii "lock-step networking" și a structurii pachetelor UDP.
- **Sunet și Muzică:** Extragerea și redarea track-urilor audio.

# Bad Respondents Detector v2.0

Aplikace pro automatickou detekci problematických respondentů ve výzkumných datech.

## 🚀 Instalace

### 1. Nainstalujte Python závislosti

```bash
pip install flask flask-cors pyreadstat pandas numpy python-docx mammoth
```

### 2. Struktura souborů

Vytvořte následující strukturu:

```
bad-respondents-detector/
├── app.py                          # Flask server
├── bad_respondents_detector.py     # Hlavní logika detekce
├── questionnaire_parser.py         # Parser dotazníků
├── spss_syntax_unified.py          # Generátor SPSS syntaxe
├── static/
│   └── index.html                  # Frontend
└── README.md
```

### 3. Spusťte aplikaci

```bash
python app.py
```

Aplikace poběží na: http://localhost:5000

## 📋 Požadované Python balíčky

- **flask** - web framework
- **flask-cors** - CORS podpora
- **pyreadstat** - čtení SAV souborů
- **pandas** - zpracování dat
- **numpy** - matematické operace
- **python-docx** - čtení DOCX souborů
- **mammoth** - alternativní DOCX parser

## 🔧 Řešení problémů

### ✗ ERROR: Failed to import modules

**Problém:** Chybí Python balíčky

**Řešení:**
```bash
pip install --upgrade pyreadstat pandas numpy python-docx mammoth flask flask-cors
```

### JSON.parse error

**Problém:** Server vrací chybu místo JSON

**Řešení:**
1. Zkontrolujte konzoli serveru (terminál kde běží `python app.py`)
2. Podívejte se na přesnou chybovou hlášku
3. Ujistěte se, že všechny moduly jsou nainstalované

### Soubory se nenahrají

**Problém:** Upload se zasekne

**Řešení:**
1. Zkontrolujte velikost SAV souboru (limit 100MB)
2. Zkontrolujte že je SAV v platném formátu
3. Podívejte se do browser console (F12) na chyby

## 🎯 Jak aplikace funguje

### 1. Detekce speeders
- Najde medián doby vyplňování
- Označí respondenty s dobou < 1/3 mediánu

### 2. AI scoring otevřených odpovědí (NOVÉ v2.0)
- Každá odpověď dostane skóre 0-1
- Penalizace za opakující se odpovědi
- Klasifikace: high risk (≤0.2), medium risk (≤0.35), ok (>0.35)

### 3. Straight-lining
- Detekce identických odpovědí v bateriích
- Práh: 2+ baterie (nebo 1+ pro dlouhé baterie)

### 4. Kombinace rizik
- **Vysoké riziko:** 2+ problémy NEBO high risk otevřené
- **Střední riziko:** 1 problém
- **Nízké riziko:** flagged ale pod hranicí

## 📊 Výstupy

### SPSS syntaxe obsahuje 3 varianty:

1. **VARIANTA 1:** Smazat VŠE podezřelé (všechny flagged)
2. **VARIANTA 2:** Smazat pouze VYSOKÉ RIZIKO (doporučeno)
3. **VARIANTA 3:** Smazat VYSOKÉ + STŘEDNÍ RIZIKO (konzervativní)

## 🔒 Bezpečnost

- Soubory se ukládají s timestampem
- Automatické mazání po zpracování
- CORS povolen pro všechny domény (změňte pro produkci)

## 📝 Changelog v2.0

- ✨ AI-based scoring otevřených odpovědí (místo binární detekce)
- ✨ Cross-question similarity detection
- ✨ Medium risk kategorie pro review
- ✨ Lepší detekce baterií (vyloučení multi-select)
- ✨ Práh 2+ baterie pro short batteries (snížení false positives)
- ✨ Vylepšený frontend s real-time feedback
- 🐛 Opraveno kódování UTF-8
- 🐛 Lepší error handling

## 👨‍💻 Autor

Perfect Crowd s.r.o.
Jan - Market Research Specialist

## 📄 Licence

Internal use only - Perfect Crowd s.r.o.

# 🚀 Quick Start Guide

## Instalace (jednoduchá)

### Windows:
1. Dvojklik na `install.bat`
2. Počkejte až se nainstalují všechny závislosti
3. Dvojklik na `start.bat`
4. Otevřete prohlížeč: http://localhost:5000

### Mac/Linux:
```bash
chmod +x install.sh
./install.sh
python app.py
```

## Použití

1. **Nahrajte SAV soubor** s daty z dotazníku
2. **Nahrajte DOCX soubor** s exportem dotazníku
3. Klikněte **"Analyzovat data"**
4. Po analýze **stáhněte SPSS syntaxi**

## Co potřebujete

- ✅ Python 3.8+ (stáhněte z python.org)
- ✅ SAV soubor s daty
- ✅ DOCX soubor s dotazníkem

## Řešení problémů

### "Chybí potřebné moduly"
```bash
pip install --upgrade pyreadstat pandas numpy python-docx mammoth flask flask-cors
```

### "Server neběží"
1. Otevřete terminál/příkazový řádek
2. Přejděte do složky s aplikací
3. Spusťte: `python app.py`

### "JSON parse error"
- Podívejte se do terminálu kde běží server
- Zkontrolujte že máte nainstalované všechny moduly
- Restartujte server (CTRL+C a znovu `python app.py`)

## Testování

Aplikace obsahuje health check:
- Otevřete: http://localhost:5000/health
- Měli byste vidět: `{"status": "ok", "modules_loaded": true}`

## Podpora

Pokud máte problémy, zkontrolujte:
1. Konzoli serveru (terminál)
2. Browser console (F12)
3. README.md pro detailní dokumentaci

---

**Perfect Crowd s.r.o. | Bad Respondents Detector v2.0**

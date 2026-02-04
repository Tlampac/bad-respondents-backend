# 🚀 RYCHLÝ DEPLOYMENT GUIDE

## Krok 1: Příprava GitHub repozitáře

```bash
# V lokálním adresáři projektu
git init
git add .
git commit -m "Initial commit - Bad Respondents Detector"

# Vytvoř nový repozitář na github.com a pak:
git remote add origin https://github.com/YOUR_USERNAME/bad-respondents-detector.git
git branch -M main
git push -u origin main
```

## Krok 2: Deploy na Render.com

### Varianta A: Automatický deploy (DOPORUČENO)

1. Jdi na https://render.com
2. Klikni **"New +"** → **"Blueprint"**
3. Připoj GitHub repozitář
4. Render automaticky detekuje `render.yaml` a nastaví vše
5. Klikni **"Apply"**
6. Čekej 5-10 minut
7. Dostaneš URL: `https://bad-respondents-detector.onrender.com`

### Varianta B: Manuální setup

1. Jdi na https://render.com
2. Klikni **"New +"** → **"Web Service"**
3. Připoj GitHub repozitář
4. Nastav:
   ```
   Name: bad-respondents-detector
   Environment: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: gunicorn app:app --bind 0.0.0.0:$PORT --timeout 300 --workers 2
   Instance Type: Free
   ```
5. Klikni **"Create Web Service"**
6. Čekej 5-10 minut

## Krok 3: První test

1. Otevři URL z Render dashboardu
2. Nahraj testovací SAV + DOCX
3. Klikni "Analyzovat data"
4. Po analýze stáhni SPSS syntax

## ⚠️ Důležité upozornění - Free tier

**Aplikace "usne" po 15 minutách neaktivity!**

První request po probuzení trvá 30-60 sekund.

### Řešení 1: Ping služba (ZDARMA)

1. Jdi na https://uptimerobot.com
2. Vytvoř účet
3. Přidej monitor:
   - Type: HTTP(s)
   - URL: `https://your-app.onrender.com/health`
   - Interval: 5 minutes
4. UptimeRobot bude pingovat aplikaci každých 5 minut

### Řešení 2: Upgrade na placený tier ($7/měsíc)

- Aplikace běží non-stop
- Více RAM a CPU
- Rychlejší start

## 🎉 Hotovo!

Aplikace běží na webu a je přístupná odkudkoli!

## Troubleshooting

### Build selhává

```bash
# Zkontroluj Python verze:
cat runtime.txt  # mělo by být python-3.11.7

# Zkontroluj závislosti:
cat requirements.txt
```

### App crashed

1. Jdi do Render dashboardu
2. Klikni na "Logs"
3. Hledej chybovou hlášku
4. Obvykle problém: nedostatek paměti → zmenši SAV soubor

### CORS errors

```python
# Ujisti se, že app.py obsahuje:
from flask_cors import CORS
CORS(app, resources={r"/api/*": {"origins": "*"}})
```

### Timeout při analýze

- Free tier má timeout 300 sekund
- Zkus menší SAV soubor (<20 MB)
- Nebo upgraduj na placený tier

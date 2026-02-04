# Bad Respondents Detector

Webová aplikace pro automatickou detekci nekvalitních respondentů v market research datech.

## Funkce

- 🚀 **Detekce speeders** - respondenti, kteří vyplnili příliš rychle
- 📝 **Analýza otevřených otázek** - detekce nesmyslných odpovědí
- 📊 **Straight-lining** - detekce monotónních odpovědí v bateriích
- 🎯 **Třístupňová rizika** - VYSOKÉ, STŘEDNÍ, NÍZKÉ
- 📥 **SPSS syntax** - automatické generování syntaxe pro čištění dat

## Technologie

- **Backend**: Flask (Python 3.11)
- **Frontend**: Vanilla JavaScript (žádné frameworky)
- **Data processing**: pandas, pyreadstat, mammoth
- **Deploy**: Render.com (free tier)

## Lokální spuštění

```bash
# Instalace závislostí
pip install -r requirements.txt

# Spuštění aplikace
python app.py

# Aplikace běží na http://localhost:5000
```

## Nasazení na Render.com (ZDARMA)

### 1. Příprava

1. Vytvoř Git repozitář na GitHubu
2. Nahraj všechny soubory z tohoto projektu

### 2. Nasazení

1. Jdi na [render.com](https://render.com)
2. Vytvoř účet (můžeš použít GitHub)
3. Klikni na **"New +"** → **"Web Service"**
4. Připoj svůj GitHub repozitář
5. Nastav:
   - **Name**: `bad-respondents-detector` (nebo jakékoli jméno)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT --timeout 300 --workers 2`
   - **Instance Type**: `Free`

6. Klikni **"Create Web Service"**

### 3. Čekání na deploy

- První deploy trvá 5-10 minut
- Render automaticky nainstaluje závislosti
- Po dokončení dostaneš URL: `https://your-app-name.onrender.com`

### 4. Hotovo!

Aplikace je živá a dostupná na webu zdarma! 🎉

## Důležité poznámky

### Limitace free tieru Render.com:

- ⚠️ **Aplikace "usne" po 15 minutách neaktivity**
  - První request po probuzení může trvat 30-60 sekund
  - Řešení: Používej ping službu (např. UptimeRobot) nebo upgraduj na placený tier
  
- 💾 **500 MB RAM limit**
  - Postačuje pro většinu analýz
  - Velké SAV soubory (>50 MB) mohou způsobit timeout
  
- ⏱️ **Build timeout 15 minut**
  - První build může trvat déle kvůli instalaci pyreadstat
  - Používáme fixované verze knihoven pro stabilitu

### Řešení problémů:

**Aplikace se zasekla při analýze:**
- Zkontroluj velikost SAV souboru (ideálně <20 MB)
- Ujisti se, že DOCX obsahuje správnou strukturu

**CORS chyby:**
- Flask-CORS je nakonfigurovaný pro povolení všech originů
- Render automaticky nastavuje HTTPS

**Python verze:**
- Vynucena Python 3.11.7 přes `runtime.txt`
- Všechny knihovny mají fixované verze v `requirements.txt`

## Struktura projektu

```
.
├── app.py                          # Flask backend
├── bad_respondents_detector.py     # Hlavní analýza
├── questionnaire_parser.py         # Parser DOCX dotazníků
├── spss_syntax_unified.py          # Generátor SPSS syntaxe
├── requirements.txt                # Python závislosti
├── Procfile                        # Render.com konfigurace
├── runtime.txt                     # Python verze
├── static/
│   └── index.html                  # Frontend aplikace
└── README.md
```

## API Endpointy

### POST /api/analyze
Analyzuje SAV + DOCX a vrací výsledky

**Request:** multipart/form-data
- `sav_file`: .sav soubor
- `docx_file`: .docx dotazník

**Response:** JSON s výsledky analýzy

### GET /api/download/{filename}
Stáhne vygenerovaný SPSS syntax soubor

### GET /health
Health check endpoint

## Autor

Perfect Crowd s.r.o. - Market Research Agency

## Licence

Proprietary - Internal use only

#!/usr/bin/env python3
"""
Identifikátor špatných respondentů
----------------------------------
Analyzuje kvalitu respondentů na základě:
1. Rychlost vyplnění (speeders - 5% nejrychlejších)
2. Nesmyslné odpovědi v otevřených otázkách
3. Straight-lining v bateriích (všechny odpovědi stejné)

Author: Claude
Date: 2026-02-03
"""

import pyreadstat
import pandas as pd
import numpy as np
import re
from datetime import datetime
from questionnaire_parser import parse_questionnaire, find_variable_names


def duration_to_seconds(duration_str):
    """Převede duration string '0:4:35' na sekundy"""
    if pd.isna(duration_str):
        return np.nan
    parts = str(duration_str).split(':')
    if len(parts) == 3:
        hours, mins, secs = map(int, parts)
        return hours * 3600 + mins * 60 + secs
    return np.nan


def is_suspicious_answer(text):
    """Detekuje nesmyslné odpovědi v otevřených otázkách"""
    if pd.isna(text) or text == '':
        return False
    
    text = str(text).strip()
    
    # Vzory nesmyslných odpovědí
    suspicious_patterns = [
        r'^-+$',           # Jen pomlčky
        r'^[aA]+$',        # Jen písmeno A (aaa, AAA)
        r'^[nN]ula$',      # "Nula"
        r'^[nN]e$',        # "Ne"
        r'^[nN]evim$',     # "Nevim"
        r'^[xX]+$',        # Jen X
        r'^\.+$',          # Jen tečky
        r'^\d+$',          # Jen čísla
    ]
    
    for pattern in suspicious_patterns:
        if re.match(pattern, text):
            return True
    
    # Velmi krátké odpovědi (1-2 znaky)
    if len(text) <= 2:
        return True
    
    return False


def analyze_respondents(sav_file, id_column=None):
    """Analyzuje bez dotazníku - používá heuristiky"""
    return _analyze_respondents_impl(sav_file, id_column, questionnaire_file=None)


def analyze_with_questionnaire(sav_file, questionnaire_file, id_column=None):
    """Analyzuje S dotazníkem - přesná detekce otázek"""
    return _analyze_respondents_impl(sav_file, id_column, questionnaire_file)


def _analyze_respondents_impl(sav_file, id_column=None, questionnaire_file=None):
    """
    Hlavní analýza kvality respondentů
    
    Args:
        sav_file: cesta k .sav souboru
        id_column: název proměnné s ID respondenta (pokud None, automaticky vybere UserPanelId nebo ExternalId)
    
    Returns:
        dict s výsledky analýzy
    """
    
    # Načtení dat
    print(f"Načítám data z: {sav_file}")
    df, meta = pyreadstat.read_sav(sav_file)
    print(f"Načteno {len(df)} respondentů, {len(df.columns)} proměnných")
    
    # Automatický výběr ID sloupce
    if id_column is None:
        # Zkontrolujeme UserPanelId - pokud existuje a není většinou prázdný
        if 'UserPanelId' in df.columns and df['UserPanelId'].notna().sum() > len(df) * 0.5:
            id_column = 'UserPanelId'
            print(f"Používám ID: UserPanelId (externí panel)")
        elif 'ExternalId' in df.columns:
            id_column = 'ExternalId'
            print(f"Používám ID: ExternalId (UserPanelId neobsahuje dostatek hodnot)")
        else:
            raise ValueError("Nenalezena ani UserPanelId ani ExternalId proměnná!")
    
    print(f"ID sloupec: {id_column}")
    
    # Převod duration
    if 'duration' in df.columns:
        df['duration_sec'] = df['duration'].apply(duration_to_seconds)
    else:
        print("VAROVÁNÍ: Proměnná 'duration' nebyla nalezena!")
        df['duration_sec'] = np.nan
    
    # Inicializace výsledků
    results = {
        'total_respondents': len(df),
        'speeders': [],
        'suspicious_open': [],
        'straight_liners': [],
        'all_bad': []
    }
    
    # 1. SPEEDERS (5% nejrychlejších)
    if not df['duration_sec'].isna().all():
        threshold = df['duration_sec'].quantile(0.05)
        speeders_mask = df['duration_sec'] <= threshold
        results['speeders'] = df[speeders_mask][id_column].tolist()
        results['speeder_threshold_sec'] = threshold
        results['speeder_threshold_min'] = threshold / 60
        print(f"\n1. SPEEDERS: {len(results['speeders'])} respondentů (≤ {threshold:.0f}s)")
    
    # 2. NESMYSLNÉ ODPOVĚDI V OTEVŘENÝCH OTÁZKÁCH
    if questionnaire_file:
        # PŘESNÝ PŘÍSTUP - použití dotazníku
        print(f"\n2. ANALÝZA OTEVŘENÝCH OTÁZEK (z dotazníku)")
        structure = parse_questionnaire(questionnaire_file)
        open_questions = structure['open_questions']
        
        if open_questions:
            print(f"   Nalezeno {len(open_questions)} otevřených otázek bez filtru:")
            for q in open_questions:
                print(f"   - {q['code']}: {q['text'][:60]}...")
            
            all_open_cols = []
            for q in open_questions:
                cols = find_variable_names(df, q['code'])
                all_open_cols.extend(cols)
            
            if all_open_cols:
                print(f"   Kontroluji {len(all_open_cols)} proměnných")
                for idx, row in df.iterrows():
                    all_suspicious = True
                    has_any_answer = False
                    
                    for col in all_open_cols:
                        val = row[col]
                        if pd.notna(val) and str(val).strip() != '':
                            has_any_answer = True
                            if not is_suspicious_answer(val):
                                all_suspicious = False
                                break
                    
                    if has_any_answer and all_suspicious:
                        results['suspicious_open'].append(row[id_column])
                
                print(f"   Podezřelé odpovědi: {len(results['suspicious_open'])} respondentů")
            else:
                print(f"   VAROVÁNÍ: Nenalezeny proměnné v datech pro otevřené otázky")
        else:
            print(f"   Žádné otevřené otázky bez filtru")
    else:
        # HEURISTICKÝ PŘÍSTUP - bez dotazníku
        # Hledáme textové proměnné (object dtype) kromě systémových
        system_cols = ['start', 'end', 'duration', 'RespondentFinishedOnQuestion', 'ExternalId', 
                       'ReferralCode', 'QuestionaryUserId', 'email', 'UserPanelId']
        open_cols = [col for col in df.columns 
                     if df[col].dtype == 'object' 
                     and col not in system_cols
                     and not col.startswith('User')]
        
        if open_cols:
            print(f"\n2. ANALÝZA OTEVŘENÝCH OTÁZEK: {len(open_cols)} textových polí (heuristika)")
            for idx, row in df.iterrows():
                all_suspicious = True
                has_any_answer = False
                
                for col in open_cols:
                    val = row[col]
                    if pd.notna(val) and str(val).strip() != '':
                        has_any_answer = True
                        if not is_suspicious_answer(val):
                            all_suspicious = False
                            break
                
                if has_any_answer and all_suspicious:
                    results['suspicious_open'].append(row[id_column])
            
            print(f"   Podezřelé odpovědi: {len(results['suspicious_open'])} respondentů")
    
    # 3. STRAIGHT-LINING V BATERIÍCH
    if questionnaire_file:
        # PŘESNÝ PŘÍSTUP - použití dotazníku
        print(f"\n3. ANALÝZA BATERIÍ (z dotazníku)")
        structure = parse_questionnaire(questionnaire_file)
        battery_questions = structure['batteries']
        
        if battery_questions:
            print(f"   Nalezeno {len(battery_questions)} baterií bez filtru:")
            for b in battery_questions:
                print(f"   - {b['code']}: {b['text'][:60]}...")
            
            valid_batteries = {}
            for b in battery_questions:
                cols = find_variable_names(df, b['code'])
                if cols and len(cols) > 3:
                    valid_batteries[b['code']] = cols
            
            if valid_batteries:
                print(f"   Kontroluji {len(valid_batteries)} baterií")
                total_items = sum(len(v) for v in valid_batteries.values())
                print(f"   Celkem položek: {total_items}")
                
                for idx, row in df.iterrows():
                    has_straight_lining = False
                    
                    for battery_name, battery_cols in valid_batteries.items():
                        values = []
                        for col in battery_cols:
                            val = row[col]
                            if pd.notna(val):
                                values.append(val)
                        
                        # Pokud má alespoň 8 odpovědí a všechny jsou stejné
                        if len(values) >= 8 and len(set(values)) == 1:
                            has_straight_lining = True
                            break
                    
                    if has_straight_lining:
                        results['straight_liners'].append(row[id_column])
                
                print(f"   Straight-lining: {len(results['straight_liners'])} respondentů")
            else:
                print(f"   VAROVÁNÍ: Nenalezeny proměnné v datech pro baterie")
        else:
            print(f"   Žádné baterie bez filtru")
    else:
        # HEURISTICKÝ PŘÍSTUP - bez dotazníku
        # Najdeme skupiny proměnných se stejným prefixem (před __)
        from collections import defaultdict
        battery_groups = defaultdict(list)
    
        for col in df.columns:
            if '__' in col and not col.startswith('User') and df[col].dtype in ['float64', 'int64']:
                prefix = col.split('__')[0]
                battery_groups[prefix].append(col)
    
        # Vybereme jen baterie s více než 3 položkami a které má vyplněné >50% respondentů
        # A které NEMAJÍ přirozeně vysoké straight-lining (jako checkboxy)
        batteries = {}
        for k, v in battery_groups.items():
            if len(v) > 3:
                # Spočítáme kolik respondentů má alespoň nějakou hodnotu
                has_data = df[v].notna().any(axis=1).sum()
                coverage = has_data / len(df)
            
                if coverage > 0.5:  # Alespoň 50% respondentů má data
                    # Spočítáme kolik má straight-lining
                    straight_count = 0
                    for idx, row in df.iterrows():
                        values = [row[c] for c in v if pd.notna(row[c])]
                        if len(values) >= 4 and len(set(values)) == 1:
                            straight_count += 1
                
                    # Pokud má <20% straight-lining, je to validní baterie pro kontrolu
                    straight_rate = straight_count / len(df)
                    if straight_rate < 0.20:
                        batteries[k] = v
    
        if batteries:
            print(f"\n3. ANALÝZA BATERIÍ: {len(batteries)} baterií nalezeno (rating baterie)")
            total_items = sum(len(v) for v in batteries.values())
            print(f"   Celkem položek v bateriích: {total_items}")
        
            for idx, row in df.iterrows():
                has_straight_lining = False
            
                # Kontrola každé baterie
                for battery_name, battery_cols in batteries.items():
                    values = []
                    for col in battery_cols:
                        val = row[col]
                        if pd.notna(val):
                            values.append(val)
                
                    # Pokud má alespoň 8 odpovědí a všechny jsou stejné
                    if len(values) >= 8 and len(set(values)) == 1:
                        has_straight_lining = True
                        break
            
                if has_straight_lining:
                    results['straight_liners'].append(row[id_column])
        
            print(f"   Straight-lining: {len(results['straight_liners'])} respondentů")
        else:
            print(f"\n3. ANALÝZA BATERIÍ: Nenalezeny žádné vhodné rating baterie")
    
    # KOMBINACE - všechny špatné respondenty (filtrujeme prázdná ID)
    # Vytvoříme rizikové skupiny
    results['risk_groups'] = {
        'speeders_only': [],           # Jen rychlí
        'open_only': [],                # Jen špatné otevřenky
        'straight_only': [],            # Jen straight-lining
        'speeders_open': [],            # Rychlí + špatné otevřenky
        'speeders_straight': [],        # Rychlí + straight-lining
        'open_straight': [],            # Špatné otevřenky + straight-lining
        'all_three': []                 # Všechny 3 problémy
    }
    
    for rid in set(results['speeders'] + results['suspicious_open'] + results['straight_liners']):
        if not rid or not str(rid).strip():
            continue
            
        is_speeder = rid in results['speeders']
        is_open = rid in results['suspicious_open']
        is_straight = rid in results['straight_liners']
        
        # Kategorizace podle kombinace
        if is_speeder and is_open and is_straight:
            results['risk_groups']['all_three'].append(rid)
        elif is_speeder and is_open:
            results['risk_groups']['speeders_open'].append(rid)
        elif is_speeder and is_straight:
            results['risk_groups']['speeders_straight'].append(rid)
        elif is_open and is_straight:
            results['risk_groups']['open_straight'].append(rid)
        elif is_speeder:
            results['risk_groups']['speeders_only'].append(rid)
        elif is_open:
            results['risk_groups']['open_only'].append(rid)
        elif is_straight:
            results['risk_groups']['straight_only'].append(rid)
    
    # Doporučení na základě rizikových skupin a délky baterie
    battery_length = 0
    if questionnaire_file:
        structure = parse_questionnaire(questionnaire_file)
        if structure['batteries']:
            # Vezmeme maximální délku baterie
            for b in structure['batteries']:
                cols = find_variable_names(df, b['code'])
                if len(cols) > battery_length:
                    battery_length = len(cols)
    
    # Vytvoříme doporučení
    results['recommendations'] = {
        'high_risk': [],      # Doporučeno smazat
        'medium_risk': [],    # Možná smazat
        'low_risk': []        # Nechat
    }
    
    # HIGH RISK - minimálně 2 problémy
    results['recommendations']['high_risk'] = (
        results['risk_groups']['all_three'] +
        results['risk_groups']['speeders_open'] +
        results['risk_groups']['speeders_straight'] +
        results['risk_groups']['open_straight']
    )
    
    # MEDIUM/LOW RISK - záleží na délce baterie
    if battery_length >= 10:
        # Dlouhé baterie - straight-lining je podezřelý
        results['recommendations']['medium_risk'] = results['risk_groups']['straight_only']
        results['recommendations']['low_risk'] = (
            results['risk_groups']['speeders_only'] +
            results['risk_groups']['open_only']
        )
    else:
        # Krátké baterie - straight-lining je OK
        results['recommendations']['low_risk'] = (
            results['risk_groups']['straight_only'] +
            results['risk_groups']['speeders_only'] +
            results['risk_groups']['open_only']
        )
    
    all_bad = set(results['speeders'] + results['suspicious_open'] + results['straight_liners'])
    # Odstranění prázdných ID
    all_bad = {x for x in all_bad if x and str(x).strip()}
    results['all_bad'] = sorted(list(all_bad))
    results['battery_length'] = battery_length
    
    print(f"\n" + "="*60)
    print(f"RIZIKOVÉ KATEGORIE:")
    print(f"  Všechny 3 problémy: {len(results['risk_groups']['all_three'])}")
    print(f"  Rychlí + špatné otevřenky: {len(results['risk_groups']['speeders_open'])}")
    print(f"  Rychlí + straight-lining: {len(results['risk_groups']['speeders_straight'])}")
    print(f"  Špatné otevřenky + straight-lining: {len(results['risk_groups']['open_straight'])}")
    print(f"  Pouze rychlí: {len(results['risk_groups']['speeders_only'])}")
    print(f"  Pouze špatné otevřenky: {len(results['risk_groups']['open_only'])}")
    print(f"  Pouze straight-lining: {len(results['risk_groups']['straight_only'])}")
    
    print(f"\n" + "="*60)
    print(f"DOPORUČENÍ (baterie {battery_length} položek):")
    print(f"  VYSOKÉ RIZIKO (doporučeno smazat): {len(results['recommendations']['high_risk'])}")
    print(f"  STŘEDNÍ RIZIKO (možná smazat): {len(results['recommendations']['medium_risk'])}")
    print(f"  NÍZKÉ RIZIKO (nechat): {len(results['recommendations']['low_risk'])}")
    
    print(f"\n" + "="*60)
    print(f"CELKEM PODEZŘELÝCH RESPONDENTŮ: {len(results['all_bad'])}")
    print("="*60)
    
    results['id_column'] = id_column  # Uložíme použitý ID sloupec
    
    return results, df


def generate_spss_syntax(results, id_column='ExternalId', output_file=None, risk_level='high'):
    """
    Generuje SPSS syntax pro vymazání špatných respondentů
    
    Args:
        results: dict s výsledky z analyze_respondents()
        id_column: název ID proměnné
        output_file: pokud zadáno, uloží syntax do souboru
        risk_level: 'high', 'medium', 'all' - která rizika smazat
    """
    
    # Vybereme IDs podle rizikové úrovně
    if risk_level == 'high':
        ids_to_delete = results['recommendations']['high_risk']
        level_desc = "VYSOKÉ RIZIKO (2+ problémy)"
    elif risk_level == 'medium':
        ids_to_delete = results['recommendations']['high_risk'] + results['recommendations']['medium_risk']
        level_desc = "VYSOKÉ + STŘEDNÍ RIZIKO"
    else:  # 'all'
        ids_to_delete = results['all_bad']
        level_desc = "VŠECHNA RIZIKA"
    
    syntax = f"""* Generováno: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.
* Analyza kvality respondentu.
* Celkem identifikovano: {len(results['all_bad'])} podezrelych respondentu.
* Mazeme: {level_desc} ({len(ids_to_delete)} respondentu).

* RIZIKOVE KATEGORIE:
* - Vsechny 3 problemy: {len(results['risk_groups']['all_three'])}.
* - Rychli + spatne otevrenky: {len(results['risk_groups']['speeders_open'])}.
* - Rychli + straight-lining: {len(results['risk_groups']['speeders_straight'])}.
* - Spatne otevrenky + straight-lining: {len(results['risk_groups']['open_straight'])}.
* - Pouze rychli: {len(results['risk_groups']['speeders_only'])}.
* - Pouze spatne otevrenky: {len(results['risk_groups']['open_only'])}.
* - Pouze straight-lining: {len(results['risk_groups']['straight_only'])}.

* 1. SPEEDERS ({len(results['speeders'])} respondentu).
* Rychlost vyplneni <= {results.get('speeder_threshold_sec', 0):.0f} sekund ({results.get('speeder_threshold_min', 0):.1f} min).

* 2. NESMYSLNE ODPOVEDI V OTEVRENYCH OTAZKACH ({len(results['suspicious_open'])} respondentu).

* 3. STRAIGHT-LINING V BATERII ({len(results['straight_liners'])} respondentu).
* Delka baterie: {results.get('battery_length', 'N/A')} polozek.

* VYMAZANI {level_desc}.
SELECT IF NOT ANY({id_column},
"""
    
    # Přidání všech ID
    for i, id_val in enumerate(ids_to_delete):
        if i == len(ids_to_delete) - 1:
            syntax += f"    '{id_val}').\n"
        else:
            syntax += f"    '{id_val}',\n"
    
    syntax += f"""
EXECUTE.

* Po vymazani by melo zustat: {results['total_respondents'] - len(ids_to_delete)} respondentu.
* (Vsech podezrelych: {len(results['all_bad'])}, mazeme: {len(ids_to_delete)}).
"""
    
    if output_file:
        with open(output_file, 'w', encoding='windows-1250') as f:
            f.write(syntax)
        print(f"\nSPSS syntax uložena do: {output_file}")
    
    return syntax


def create_detailed_report(results, df, id_column='ExternalId', output_file=None):
    """
    Vytvoří detailní report s informacemi o každém podezřelém respondentovi
    """
    
    report = f"""DETAILNÍ REPORT - IDENTIFIKACE ŠPATNÝCH RESPONDENTŮ
{'='*80}
Datum analýzy: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Celkem respondentů: {results['total_respondents']}
Podezřelých respondentů: {len(results['all_bad'])}
Procento podezřelých: {len(results['all_bad'])/results['total_respondents']*100:.1f}%

SOUHRN PROBLÉMŮ:
- Speeders (příliš rychlé vyplnění): {len(results['speeders'])}
- Nesmyslné odpovědi v otevřených otázkách: {len(results['suspicious_open'])}
- Straight-lining v baterii: {len(results['straight_liners'])}

{'='*80}

SEZNAM PODEZŘELÝCH RESPONDENTŮ:
{'='*80}
"""
    
    for rid in results['all_bad']:
        problems = []
        if rid in results['speeders']:
            problems.append('SPEEDER')
        if rid in results['suspicious_open']:
            problems.append('NESMYSLNÉ ODPOVĚDI')
        if rid in results['straight_liners']:
            problems.append('STRAIGHT-LINING')
        
        report += f"\nID: {rid}\n"
        report += f"  Problémy: {', '.join(problems)}\n"
        
        # Najdeme řádek v datech
        row = df[df[id_column] == rid]
        if not row.empty:
            row = row.iloc[0]
            if 'duration' in df.columns:
                report += f"  Čas vyplnění: {row['duration']}\n"
    
    report += f"\n{'='*80}\n"
    
    if output_file:
        with open(output_file, 'w', encoding='windows-1250') as f:
            f.write(report)
        print(f"Detailní report uložen do: {output_file}")
    
    return report


if __name__ == "__main__":
    # Příklad použití S DOTAZNÍKEM
    sav_file = "/mnt/user-data/uploads/Tracking_znacky_J_T_Banka_0126_-_od_50k_-_2026-02-03-v2.sav"
    docx_file = "/mnt/user-data/uploads/Tracking_značky_J_T_Banka_0126_-_od_50k_-_2026-02-03.docx"
    
    # Analýza S dotazníkem - DOPORUČENO
    results, df = analyze_with_questionnaire(sav_file, docx_file)
    
    # Generování SPSS syntax - 3 varianty
    syntax_high = generate_spss_syntax(results, id_column=results['id_column'], 
                                       output_file="/home/claude/delete_bad_HIGH_RISK.sps", 
                                       risk_level='high')
    
    syntax_medium = generate_spss_syntax(results, id_column=results['id_column'], 
                                         output_file="/home/claude/delete_bad_MEDIUM_RISK.sps", 
                                         risk_level='medium')
    
    syntax_all = generate_spss_syntax(results, id_column=results['id_column'], 
                                      output_file="/home/claude/delete_bad_ALL.sps", 
                                      risk_level='all')
    
    # Detailní report
    report = create_detailed_report(results, df, id_column=results['id_column'], 
                                    output_file="/home/claude/bad_respondents_report.txt")
    
    print("\n" + report[:2000])

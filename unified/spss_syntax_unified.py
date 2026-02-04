def generate_spss_syntax_unified(results, id_column='ExternalId', output_file=None):
    """
    Generuje SPSS syntax se všemi 3 variantami v jednom souboru.
    Každá varianta je připravená ke spuštění - stačí smazat ostatní varianty.
    """
    
    ids_high = results['recommendations']['high_risk']
    ids_medium = results['recommendations']['high_risk'] + results['recommendations']['medium_risk']
    ids_all = results['all_bad']
    
    from datetime import datetime
    
    syntax = f"""* ============================================================================.
* IDENTIFIKACE ŠPATNÝCH RESPONDENTŮ
* ============================================================================.
* Generováno: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.
* Celkem analyzováno: {results['total_respondents']} respondentů.
* Celkem identifikováno: {len(results['all_bad'])} podezřelých.
*
* RIZIKOVÉ KATEGORIE:
* - Všechny 3 problémy: {len(results['risk_groups']['all_three'])}.
* - Rychlí + špatné otevřenky: {len(results['risk_groups']['speeders_open'])}.
* - Rychlí + straight-lining: {len(results['risk_groups']['speeders_straight'])}.
* - Špatné otevřenky + straight-lining: {len(results['risk_groups']['open_straight'])}.
* - Pouze rychlí: {len(results['risk_groups']['speeders_only'])}.
* - Pouze špatné otevřenky: {len(results['risk_groups']['open_only'])}.
* - Pouze straight-lining: {len(results['risk_groups']['straight_only'])}.
*
* DETEKOVANÉ PROBLÉMY:
* 1. SPEEDERS: {len(results['speeders'])} respondentů.
*    Rychlost <= {results.get('speeder_threshold_sec', 0):.0f}s ({results.get('speeder_threshold_min', 0):.1f} min).
* 2. NESMYSLNÉ ODPOVĚDI: {len(results['suspicious_open'])} respondentů.
* 3. STRAIGHT-LINING: {len(results['straight_liners'])} respondentů.
*    Délka baterie: {results.get('battery_length', 'N/A')} položek.
*
* ============================================================================.
* TŘI VARIANTY - vyberte jednu a SMAŽTE ostatní dvě sekce.
* ============================================================================.


* ============================================================================.
* VARIANTA 1: VYSOKÉ RIZIKO (DOPORUČENO).
* Maže {len(ids_high)} respondentů. Zůstane: {results['total_respondents'] - len(ids_high)}.
* ============================================================================.
SELECT IF NOT ANY({id_column},
"""
    
    for i, id_val in enumerate(ids_high):
        if i == len(ids_high) - 1:
            syntax += f"    '{id_val}').\n"
        else:
            syntax += f"    '{id_val}',\n"
    
    syntax += "EXECUTE.\n\n\n"
    
    syntax += f"""* ============================================================================.
* VARIANTA 2: STŘEDNÍ RIZIKO.
* Maže {len(ids_medium)} respondentů. Zůstane: {results['total_respondents'] - len(ids_medium)}.
* ============================================================================.
SELECT IF NOT ANY({id_column},
"""
    
    for i, id_val in enumerate(ids_medium):
        if i == len(ids_medium) - 1:
            syntax += f"    '{id_val}').\n"
        else:
            syntax += f"    '{id_val}',\n"
    
    syntax += "EXECUTE.\n\n\n"
    
    syntax += f"""* ============================================================================.
* VARIANTA 3: VŠICHNI PODEZŘELÍ.
* Maže {len(ids_all)} respondentů. Zůstane: {results['total_respondents'] - len(ids_all)}.
* ============================================================================.
SELECT IF NOT ANY({id_column},
"""
    
    for i, id_val in enumerate(ids_all):
        if i == len(ids_all) - 1:
            syntax += f"    '{id_val}').\n"
        else:
            syntax += f"    '{id_val}',\n"
    
    syntax += "EXECUTE.\n"
    
    if output_file:
        with open(output_file, 'w', encoding='windows-1250') as f:
            f.write(syntax)
        print(f"\nSPSS syntax uložena do: {output_file}")
        print(f"  INSTRUKCE: Vyberte JEDNU variantu a smažte ostatní dvě sekce SELECT IF")
        print(f"  - VYSOKÉ RIZIKO: {len(ids_high)} respondentů")
        print(f"  - STŘEDNÍ RIZIKO: {len(ids_medium)} respondentů")  
        print(f"  - VŠICHNI: {len(ids_all)} respondentů")
    
    return syntax

"""
SPSS Syntax Generator - generates SPSS syntax for deleting bad respondents.
Unified version supporting multiple syntax variants.
"""

from datetime import datetime


def generate_spss_syntax_unified(results, id_column='ExternalId', output_file=None):
    """
    Generate SPSS syntax with 3 variants for deleting bad respondents.
    """
    lines = []
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    lines.append(f"* ================================================================.")
    lines.append(f"* Bad Respondents Detector v2.0 - SPSS Syntax.")
    lines.append(f"* Generated: {timestamp}.")
    lines.append(f"* ================================================================.")
    lines.append(f"* Total respondents: {results['total_respondents']}.")
    lines.append(f"* Speeders: {len(results['speeders'])}.")
    lines.append(f"* Suspicious open-ended (high risk): {len(results['suspicious_open'])}.")
    lines.append(f"* Suspicious open-ended (medium risk): {len(results.get('suspicious_open_medium', []))}.")
    lines.append(f"* Straight-liners: {len(results['straight_liners'])}.")
    lines.append(f"* Total flagged: {len(results['all_bad'])}.")
    lines.append(f"* HIGH RISK (recommend delete): {len(results['recommendations']['high_risk'])}.")
    lines.append(f"* MEDIUM RISK (consider delete): {len(results['recommendations']['medium_risk'])}.")
    lines.append(f"* ================================================================.")
    lines.append(f"")
    
    def format_id_list(ids, id_col):
        """Format list of IDs for SPSS syntax."""
        if not ids:
            return ""
        
        formatted = []
        for x in ids:
            if isinstance(x, str) or (isinstance(x, float) and not x.is_integer()):
                formatted.append(f"'{str(x)}'")
            else:
                formatted.append(str(int(x)) if isinstance(x, float) else str(x))
        
        # Split into lines of max ~10 IDs for readability
        chunks = []
        for i in range(0, len(formatted), 10):
            chunk = ", ".join(formatted[i:i+10])
            chunks.append(chunk)
        
        return ",\n    ".join(chunks)
    
    # Variant 1: Delete ALL flagged
    all_bad = results['all_bad']
    lines.append(f"* === VARIANTA 1: Smazat VSE podezrele ({len(all_bad)} respondents) ===.")
    if all_bad:
        id_list = format_id_list(all_bad, id_column)
        lines.append(f"SELECT IF NOT ANY({id_column},")
        lines.append(f"    {id_list}).")
        lines.append(f"EXECUTE.")
    else:
        lines.append(f"* Zadni podezreli respondenti nenalezeni.")
    lines.append(f"")
    
    # Variant 2: Delete only HIGH RISK
    high_risk = results['recommendations']['high_risk']
    lines.append(f"* === VARIANTA 2: Smazat pouze VYSOKE RIZIKO ({len(high_risk)} respondents) ===.")
    if high_risk:
        id_list = format_id_list(high_risk, id_column)
        lines.append(f"* SELECT IF NOT ANY({id_column},")
        lines.append(f"*     {id_list}).")
        lines.append(f"* EXECUTE.")
    else:
        lines.append(f"* Zadni vysoko rizikovi respondenti nenalezeni.")
    lines.append(f"")
    
    # Variant 3: Delete HIGH + MEDIUM
    hm_risk = high_risk + results['recommendations']['medium_risk']
    lines.append(f"* === VARIANTA 3: Smazat VYSOKE + STREDNI RIZIKO ({len(hm_risk)} respondents) ===.")
    if hm_risk:
        id_list = format_id_list(hm_risk, id_column)
        lines.append(f"* SELECT IF NOT ANY({id_column},")
        lines.append(f"*     {id_list}).")
        lines.append(f"* EXECUTE.")
    else:
        lines.append(f"* Zadni respondenti v teto kategorii.")
    lines.append(f"")
    
    lines.append(f"* === KONEC SYNTAXE ===.")
    
    syntax = "\n".join(lines)
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(syntax)
    
    return syntax

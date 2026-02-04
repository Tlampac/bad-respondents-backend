#!/usr/bin/env python3
"""
Parser dotazníku - extrahuje strukturu otázek z DOCX
"""

import mammoth
import re


def parse_questionnaire(docx_file):
    """
    Parsuje dotazník a extrahuje otevřené otázky a baterie
    
    Returns:
        dict: {
            'open_questions': [{'code': 'A1a', 'type': 'multi_field'/'text', 'text': '...'}],
            'batteries': [{'code': 'A4', 'type': 'single_choice', 'text': '...'}]
        }
    """
    
    # Pokusíme se načíst mammoth, pokud selže, použijeme python-docx
    text = None
    try:
        with open(docx_file, 'rb') as f:
            result = mammoth.extract_raw_text(f)
            text = result.value
    except Exception as e:
        print(f"Mammoth selhalo ({e}), zkouším python-docx...")
        try:
            import docx
            doc = docx.Document(docx_file)
            text = '\n'.join([para.text for para in doc.paragraphs])
        except Exception as e2:
            print(f"Python-docx také selhalo: {e2}")
            return {'open_questions': [], 'batteries': []}
    
    if not text:
        return {'open_questions': [], 'batteries': []}
    
    lines = text.split('\n')
    
    open_questions = []
    batteries = []
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Hledáme kód otázky (A1., B2., C3a., atd.)
        match = re.match(r'^([A-Z]\d+[a-z]?)\.\s+(.+)', line)
        if match:
            code = match.group(1)
            question_text = match.group(2)
            
            # Hledáme typ otázky v následujících řádcích
            question_type = None
            has_condition = False
            
            # Koukáme až 50 řádků dopředu (některé baterie mají dlouhé seznamy)
            for j in range(i+1, min(i+50, len(lines))):
                check_line = lines[j]
                
                # Zjistíme typ
                if 'Vyberte typ otázky::' in check_line:
                    question_type = check_line
                
                # Zjistíme zda má podmínku - musí být AŽ PO "Vyberte typ otázky"
                if question_type and ('Pravidla' in check_line or 'ISCHECKED' in check_line):
                    has_condition = True
                    break
                
                # Pokud narazíme na další otázku, končíme
                if re.match(r'^[A-Z]\d+[a-z]?\.\s+', check_line):
                    break
            
            # Zpracujeme jen otázky BEZ podmínky
            if question_type and not has_condition:
                if 'OTEVŘENÁ OTÁZKA - VÍCE POLÍ PRO ODPOVĚĎ' in question_type:
                    open_questions.append({
                        'code': code,
                        'type': 'multi_field',
                        'text': question_text[:100]
                    })
                elif 'OTEVŘENÁ OTÁZKA - ODPOVĚĎ TEXT' in question_type:
                    open_questions.append({
                        'code': code,
                        'type': 'text',
                        'text': question_text[:100]
                    })
                elif 'BATERIE OTÁZEK - JEDNA MOŽNÁ ODPOVĚĎ' in question_type:
                    batteries.append({
                        'code': code,
                        'type': 'single_choice',
                        'text': question_text[:100]
                    })
        
        i += 1
    
    return {
        'open_questions': open_questions,
        'batteries': batteries
    }


def find_variable_names(df, question_code):
    """
    Najde proměnné v datech odpovídající kódu otázky (např. A1a -> QA1a)
    
    Args:
        df: pandas DataFrame s daty
        question_code: kód otázky z dotazníku (např. 'A1a', 'B2')
    
    Returns:
        list: názvy proměnných
    """
    
    # Možné varianty prefixu
    variants = [
        f'Q{question_code}',      # QA1a
        f'Q{question_code.upper()}',  # QA1A
        f'{question_code}',       # A1a (pokud by nebylo Q)
    ]
    
    matching_vars = []
    for col in df.columns:
        for variant in variants:
            if col.startswith(variant):
                matching_vars.append(col)
                break
    
    return sorted(list(set(matching_vars)))


if __name__ == "__main__":
    # Test
    import sys
    
    if len(sys.argv) > 1:
        docx_file = sys.argv[1]
    else:
        docx_file = "/mnt/user-data/uploads/Tracking_značky_J_T_Banka_0126_-_od_50k_-_2026-02-03.docx"
    
    print(f"Parsování: {docx_file}\n")
    structure = parse_questionnaire(docx_file)
    
    print("=== OTEVŘENÉ OTÁZKY (bez podmínky) ===")
    for q in structure['open_questions']:
        print(f"{q['code']} ({q['type']}): {q['text']}")
    
    print(f"\n=== BATERIE (bez podmínky) ===")
    for b in structure['batteries']:
        print(f"{b['code']}: {b['text']}")

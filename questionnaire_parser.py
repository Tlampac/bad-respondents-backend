"""
Questionnaire Parser - reads DOCX questionnaire files and extracts structure.
Identifies: open questions, batteries, single-choice, multi-choice questions.
"""

import re

try:
    import mammoth
except ImportError:
    mammoth = None

try:
    from docx import Document as DocxDocument
except ImportError:
    DocxDocument = None


def parse_questionnaire(docx_file):
    """
    Parse a DOCX questionnaire file and extract its structure.
    
    Returns dict with:
    - open_questions: list of open-ended questions (without filters)
    - batteries: list of battery questions (matrix/grid)
    - all_questions: list of all questions
    """
    
    text = extract_text(docx_file)
    
    if not text:
        return {'open_questions': [], 'batteries': [], 'all_questions': []}
    
    return parse_structure(text)


def extract_text(docx_file):
    """Extract text from DOCX file."""
    # Try mammoth first (better for complex docs)
    if mammoth:
        try:
            with open(docx_file, 'rb') as f:
                result = mammoth.extract_raw_text(f)
                return result.value
        except Exception:
            pass
    
    # Fallback to python-docx
    if DocxDocument:
        try:
            doc = DocxDocument(docx_file)
            paragraphs = [p.text for p in doc.paragraphs]
            return '\n'.join(paragraphs)
        except Exception:
            pass
    
    return None


def parse_structure(text):
    """Parse questionnaire text into structured format."""
    
    questions = []
    open_questions = []
    batteries = []
    
    lines = text.split('\n')
    
    current_question = None
    current_options = []
    current_type = None
    has_filter = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Detect question start (Q1, Q2, Q6aB2, etc.)
        q_match = re.match(r'^(Q\d+[a-zA-Z0-9]*(?:B\d+)*(?:B\d+)*)\.\s*(.*)', line)
        
        if q_match:
            # Save previous question
            if current_question:
                q_info = {
                    'code': current_question,
                    'text': current_text,
                    'type': current_type,
                    'options': current_options,
                    'has_filter': has_filter
                }
                questions.append(q_info)
                
                # Classify
                if current_type == 'open' and not has_filter:
                    open_questions.append(q_info)
                elif current_type == 'battery':
                    q_info['items'] = current_options
                    batteries.append(q_info)
            
            # Start new question
            current_question = q_match.group(1)
            current_text = q_match.group(2).strip()
            current_options = []
            current_type = None
            has_filter = False
            continue
        
        # Detect question type
        type_patterns = {
            'open': [
                r'OTEVŘENÁ OTÁZKA',
                r'ODPOVĚĎ TEXT',
                r'OTEVŘENÁ',
            ],
            'battery': [
                r'BATERIE OTÁZEK',
                r'BATERIE',
            ],
            'single': [
                r'JEDNA MOŽNÁ ODPOVĚĎ',
            ],
            'multi': [
                r'VÍCE MOŽNÝCH ODPOVĚDÍ',
            ],
            'text_only': [
                r'POUZE TEXT',
            ],
            'end': [
                r'KONEC DOTAZNÍKU',
                r'VYLOUČENÍ RESPONDENTA',
            ]
        }
        
        for q_type, patterns in type_patterns.items():
            for pattern in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    current_type = q_type
                    break
        
        # Detect filters/rules
        if re.search(r'IF\s*\(.*ISCHECKED', line, re.IGNORECASE):
            has_filter = True
        if re.search(r'THEN\s+EXIT', line, re.IGNORECASE):
            has_filter = True
        if re.search(r'Pravidla', line, re.IGNORECASE):
            has_filter = True
        
        # Collect options (lines starting with -)
        if line.startswith('-') or line.startswith('•'):
            option_text = line.lstrip('-•').strip()
            if option_text and not any(re.search(p, option_text, re.IGNORECASE) 
                                       for patterns in type_patterns.values() 
                                       for p in patterns):
                if not re.search(r'Nastavení otázky|Povinná|Délka textu|Min\.|Max\.|Zvolených|Pravidla|IF\s*\(', option_text, re.IGNORECASE):
                    current_options.append(option_text)
    
    # Don't forget the last question
    if current_question:
        q_info = {
            'code': current_question,
            'text': current_text,
            'type': current_type,
            'options': current_options,
            'has_filter': has_filter
        }
        questions.append(q_info)
        
        if current_type == 'open' and not has_filter:
            open_questions.append(q_info)
        elif current_type == 'battery':
            q_info['items'] = current_options
            batteries.append(q_info)
    
    print(f"   Questionnaire parser results:")
    print(f"   - Total questions: {len(questions)}")
    print(f"   - Open questions (no filter): {len(open_questions)}")
    print(f"   - Batteries: {len(batteries)}")
    
    return {
        'open_questions': open_questions,
        'batteries': batteries,
        'all_questions': questions
    }

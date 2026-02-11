"""
Bad Respondents Detector v2.0
- Scoring-based open-ended answer detection (instead of binary)
- Cross-question similarity detection
- Improved speeder detection
- Straight-lining detection from questionnaire batteries
"""

import pyreadstat
import pandas as pd
import numpy as np
import re
import os
from datetime import datetime
from difflib import SequenceMatcher

# Import questionnaire parser
try:
    from questionnaire_parser import parse_questionnaire
except ImportError:
    parse_questionnaire = None


# =============================================================================
# OPEN-ENDED ANSWER QUALITY SCORING (NEW v2.0)
# =============================================================================

def answer_quality_score(text):
    """
    Score an open-ended answer from 0 (worst) to 1 (best).
    
    NOTE: Scoring is primarily LENGTH-BASED. This is a conscious trade-off:
    short but meaningful answers (e.g. "Protože je drahá.") may score lower
    than expected. That's why 'medium_risk' category exists as "review" not
    "auto-delete". Future improvement: add Claude API call for content
    relevance assessment.
    
    Score tiers:
    0.0 - 0.05: Gibberish, filler characters
    0.1:         Explicit non-answers (nevím, nic, nwm...)
    0.2:         Single word answer
    0.3:         Two word answer  
    0.45:        3-4 word answer
    0.65:        5-8 word answer
    0.8+:        Substantial answer (9+ words)
    """
    if pd.isna(text) or str(text).strip() == '':
        return 0.0
    
    t = str(text).strip()
    t_lower = t.lower().rstrip('.,!? ')
    words = t.split()
    word_count = len(words)
    
    # --- Level 0.05: Filler characters (dots, dashes, repeated chars) ---
    clean_text = re.sub(r'[.\-_!?,\s]', '', t)
    if len(clean_text) < 2 and len(t) > 3:
        return 0.05
    if re.search(r'(.)\1{9,}', t) or re.search(r'\.{10,}|_{10,}|-{10,}|x{5,}', t_lower):
        return 0.05
    
    # --- Level 0.05: Gibberish (random consonants) ---
    alpha = re.sub(r'[^a-záčďéěíňóřšťúůýž]', '', t_lower)
    if len(alpha) > 8:
        vowels = set('aeiouyáéíóúůýě')
        consonant_count = sum(1 for c in alpha if c not in vowels)
        if consonant_count / len(alpha) > 0.85:
            return 0.05
    
    # --- Level 0.1: Explicit non-answers ---
    non_answers = {
        'nevím', 'nevim', 'nwm', 'nic', 'xxx', 'nee', 'ne', 'ok', 'oká',
        'žádné', 'zadne', 'žádný', 'zadny', 'nebim', 'nic mě nenapadá',
        'nic moc', 'nemám', 'nemam', 'bez názoru', 'bez komentáře',
        'hmm', 'hm', 'hmmm', 'hm...', 'fajn', '.', '..', '...', '-', '--',
        'no', 'noo', 'jo', 'jj', 'nn', 'idk', 'nic mne nenapada',
        'nic me nenapada', 'bez komentare', 'nic zvláštního', 'nic zvlastniho',
        'nic extra', 'nevím co napsat', 'nevim co napsat'
    }
    if t_lower in non_answers:
        return 0.1
    
    # --- Level 0.2: Single word ---
    if word_count == 1:
        return 0.2
    
    # --- Level 0.3: Two words ---
    if word_count == 2:
        return 0.3
    
    # --- Level 0.45: 3-4 words ---
    if word_count <= 4:
        return 0.45
    
    # --- Level 0.65: 5-8 words ---
    if word_count <= 8:
        return 0.65
    
    # --- Level 0.8: 9-15 words ---
    if word_count <= 15:
        return 0.8
    
    # --- Level 0.85-1.0: Substantial answer ---
    return min(1.0, 0.85 + (word_count - 15) * 0.01)


def cross_question_similarity(answers):
    """
    Check if answers are suspiciously similar across questions.
    Returns a penalty score 0-0.15 to subtract from average.
    """
    clean = [a.strip().lower() for a in answers if a.strip()]
    if len(clean) < 2:
        return 0
    
    unique = set(clean)
    
    # All identical answers
    if len(unique) == 1 and len(clean) >= 3:
        return 0.15
    
    # Almost all identical (e.g., 3 out of 4 the same)
    if len(unique) <= 2 and len(clean) >= 4:
        most_common = max(set(clean), key=clean.count)
        if clean.count(most_common) >= 3:
            return 0.12
    
    # Near-duplicates (using string similarity)
    sims = []
    for i in range(len(clean)):
        for j in range(i + 1, len(clean)):
            sim = SequenceMatcher(None, clean[i], clean[j]).ratio()
            sims.append(sim)
    
    avg_sim = sum(sims) / len(sims) if sims else 0
    
    # Also check: how many pairs are very similar (>0.7)?
    high_sim_pairs = sum(1 for s in sims if s > 0.7)
    total_pairs = len(sims)
    
    if avg_sim > 0.8:
        return 0.12
    elif avg_sim > 0.6 or (high_sim_pairs >= total_pairs * 0.5):
        return 0.08
    elif avg_sim > 0.4:
        return 0.04
    
    return 0


def classify_open_ended_quality(scores_list, similarity_penalty):
    """
    Classify respondent based on their average open-ended quality score.
    
    Returns: 'high_risk', 'medium_risk', or 'ok'
    """
    if not scores_list:
        return 'ok'
    
    avg_score = sum(scores_list) / len(scores_list)
    adjusted_score = avg_score - similarity_penalty
    
    if adjusted_score <= 0.2:
        return 'high_risk'
    elif adjusted_score <= 0.35:
        return 'medium_risk'
    else:
        return 'ok'


# =============================================================================
# LEGACY COMPATIBILITY: is_suspicious_answer (now wraps scoring)
# =============================================================================

def is_suspicious_answer(text):
    """Legacy function - returns True if answer scores below 0.15"""
    return answer_quality_score(text) <= 0.15


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def find_variable_names(df, q_code):
    """Find matching variable names in DataFrame for a question code."""
    q_code_clean = q_code.replace('.', '').strip()
    matches = []
    
    for col in df.columns:
        if col.upper() == f'Q{q_code_clean}'.upper():
            matches.append(col)
        elif col.upper() == f'QQ{q_code_clean}'.upper():
            matches.append(col)
        elif col.upper().startswith(f'Q{q_code_clean}__'.upper()):
            matches.append(col)
        elif col.upper().startswith(f'QQ{q_code_clean}__'.upper()):
            matches.append(col)
    
    if not matches:
        for col in df.columns:
            if q_code_clean.upper() in col.upper():
                matches.append(col)
    
    return matches


def find_id_column(df):
    """Find the best ID column in the DataFrame."""
    preferred = ['ExternalId', 'UserPanelId', 'QuestionaryUserId', 'email', 'ReferralCode']
    for col_name in preferred:
        if col_name in df.columns:
            non_null = df[col_name].dropna()
            if len(non_null) > 0 and non_null.nunique() > len(df) * 0.5:
                return col_name
    
    for col in df.columns:
        if 'id' in col.lower() and col not in ['RespondentFinishedOnQuestion']:
            non_null = df[col].dropna()
            if len(non_null) > 0 and non_null.nunique() > len(df) * 0.5:
                return col
    
    return df.columns[0]


def parse_duration_to_seconds(duration_val):
    """Parse duration value to seconds (handles various formats).
    Supports: H:MM:SS, H:MM:SS.ms, numeric seconds, Czech decimal comma.
    Logs a warning if parsing fails so user knows why speeders may be missing.
    """
    if pd.isna(duration_val):
        return None
    
    d = str(duration_val).strip()
    if not d:
        return None
    
    # Format "H:MM:SS" or "H:MM:SSs" or "H:MM:SS.ms"
    d_clean = d.rstrip('s')
    parts = d_clean.split(':')
    if len(parts) == 3:
        try:
            hours = int(parts[0])
            minutes = int(parts[1])
            # Handle seconds with decimal part (e.g., "23.5")
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        except ValueError:
            pass
    
    # Already a number (seconds) - try direct float
    try:
        return float(d)
    except ValueError:
        pass
    
    # Czech decimal format: "123,4" → "123.4"
    if ',' in d:
        try:
            return float(d.replace(',', '.'))
        except ValueError:
            pass
    
    print(f"   WARNING: Could not parse duration value: '{d}' — this respondent will be skipped for speeder detection")
    return None


# =============================================================================
# MAIN ANALYSIS FUNCTION
# =============================================================================

def analyze_with_questionnaire(sav_file, docx_file=None):
    """
    Main analysis function. Reads SAV file and optionally a DOCX questionnaire.
    
    Returns:
        results: dict with all detection results
        df: the DataFrame
    """
    print("=" * 80)
    print("BAD RESPONDENTS DETECTOR v2.0")
    print("=" * 80)
    
    # Read SAV file
    df, meta = pyreadstat.read_sav(sav_file)
    print(f"\nData: {len(df)} respondents, {len(df.columns)} variables")
    
    # Find ID column
    id_column = find_id_column(df)
    print(f"ID column: {id_column}")
    
    # Initialize results
    results = {
        'total_respondents': len(df),
        'id_column': id_column,
        'speeders': [],
        'suspicious_open': [],
        'suspicious_open_medium': [],  # NEW: medium risk open-ended
        'straight_liners': [],
        'risk_groups': {
            'all_three': [],
            'speeders_open': [],
            'speeders_straight': [],
            'open_straight': [],
            'speeders_only': [],
            'open_only': [],
            'straight_only': []
        },
        'recommendations': {
            'high_risk': [],
            'medium_risk': [],
            'low_risk': []
        },
        'all_bad': [],
        'open_ended_scores': {},  # NEW: per-respondent scoring details
    }
    
    # Parse questionnaire if provided
    structure = None
    if docx_file and parse_questionnaire:
        try:
            structure = parse_questionnaire(docx_file)
            print(f"Questionnaire parsed: {len(structure.get('open_questions', []))} open Qs, "
                  f"{len(structure.get('batteries', []))} batteries")
        except Exception as e:
            print(f"Warning: Could not parse questionnaire: {e}")
    
    # =========================================================================
    # 1. SPEEDERS DETECTION
    # =========================================================================
    print(f"\n1. SPEEDERS DETECTION")
    
    duration_col = None
    for col_name in ['duration', 'Duration', 'DURATION', 'interview_length']:
        if col_name in df.columns:
            duration_col = col_name
            break
    
    if duration_col:
        durations_sec = []
        for val in df[duration_col]:
            sec = parse_duration_to_seconds(val)
            if sec is not None:
                durations_sec.append(sec)
            else:
                durations_sec.append(None)
        
        df['_duration_sec'] = durations_sec
        valid_durations = [d for d in durations_sec if d is not None and d > 0]
        
        if valid_durations:
            median_duration = np.median(valid_durations)
            # Threshold: less than 1/3 of median
            speeder_threshold = median_duration / 3
            
            results['speeder_threshold_sec'] = round(speeder_threshold)
            results['speeder_threshold_min'] = round(speeder_threshold / 60, 1)
            
            print(f"   Median duration: {median_duration:.0f}s ({median_duration/60:.1f} min)")
            print(f"   Speeder threshold: < {speeder_threshold:.0f}s ({speeder_threshold/60:.1f} min)")
            
            for idx, row in df.iterrows():
                dur = row.get('_duration_sec')
                if dur is not None and dur < speeder_threshold:
                    results['speeders'].append(row[id_column])
            
            print(f"   Speeders found: {len(results['speeders'])}")
        else:
            print(f"   No valid duration data found")
    else:
        print(f"   No duration column found")
    
    # =========================================================================
    # 2. OPEN-ENDED ANSWER QUALITY (NEW SCORING APPROACH v2.0)
    # =========================================================================
    print(f"\n2. OPEN-ENDED ANSWER QUALITY (scoring v2.0)")
    
    all_open_cols = []
    
    if structure and structure.get('open_questions'):
        open_questions = structure['open_questions']
        print(f"   From questionnaire: {len(open_questions)} open questions")
        for q in open_questions:
            print(f"   - {q['code']}: {q['text'][:60]}...")
            cols = find_variable_names(df, q['code'])
            all_open_cols.extend(cols)
    
    # Fallback: find text columns heuristically
    if not all_open_cols:
        system_cols = {'start', 'end', 'duration', 'RespondentFinishedOnQuestion', 
                       'ExternalId', 'ReferralCode', 'QuestionaryUserId', 'email', 
                       'UserPanelId', '_duration_sec'}
        for col in df.columns:
            if (df[col].dtype == 'object' 
                and col not in system_cols 
                and not col.startswith('User')
                and not col.endswith('_jina')):  # Skip "jiné" text fields
                # Check if it's actually an open-ended (has varied content, not coded)
                non_null = df[col].dropna()
                if len(non_null) > 0:
                    avg_len = non_null.str.len().mean()
                    if avg_len > 3:  # More than just codes
                        all_open_cols.append(col)
        print(f"   Heuristic detection: {len(all_open_cols)} text columns")
    
    if all_open_cols:
        # Deduplicate
        all_open_cols = list(dict.fromkeys(all_open_cols))
        print(f"   Analyzing {len(all_open_cols)} open-ended columns: {all_open_cols}")
        
        for idx, row in df.iterrows():
            resp_id = row[id_column]
            answers = []
            scores = []
            
            for col in all_open_cols:
                val = row[col]
                if pd.notna(val) and str(val).strip() != '':
                    answers.append(str(val).strip())
                    scores.append(answer_quality_score(val))
            
            if not scores:
                continue
            
            # Calculate similarity penalty
            sim_penalty = cross_question_similarity(answers)
            
            # Classify
            avg_score = sum(scores) / len(scores)
            adjusted_score = avg_score - sim_penalty
            
            # Store detailed scores
            results['open_ended_scores'][resp_id] = {
                'avg_score': round(avg_score, 2),
                'similarity_penalty': round(sim_penalty, 2),
                'adjusted_score': round(adjusted_score, 2),
                'individual_scores': [round(s, 2) for s in scores],
                'answers': answers
            }
            
            classification = classify_open_ended_quality(scores, sim_penalty)
            
            if classification == 'high_risk':
                results['suspicious_open'].append(resp_id)
            elif classification == 'medium_risk':
                results['suspicious_open_medium'].append(resp_id)
        
        print(f"   High risk (score ≤ 0.2): {len(results['suspicious_open'])} respondents")
        print(f"   Medium risk (score ≤ 0.35): {len(results['suspicious_open_medium'])} respondents")
    else:
        print(f"   No open-ended columns found")
    
    # =========================================================================
    # 3. STRAIGHT-LINING IN BATTERIES
    # =========================================================================
    print(f"\n3. STRAIGHT-LINING DETECTION")
    
    battery_groups = []
    
    if structure and structure.get('batteries'):
        for bat in structure['batteries']:
            q_code = bat['code']
            items = bat.get('items', [])
            cols = find_variable_names(df, q_code)
            
            if len(cols) >= 4:  # Only check batteries with 4+ items
                battery_groups.append({
                    'code': q_code,
                    'columns': cols,
                    'item_count': len(cols)
                })
                print(f"   Battery {q_code}: {len(cols)} items")
    
    # Fallback: detect batteries by column naming pattern (QXX__1, QXX__2, ...)
    if not battery_groups:
        col_groups = {}
        for col in df.columns:
            match = re.match(r'(Q+\w+?)__(\d+)$', col)
            if match:
                base = match.group(1)
                if base not in col_groups:
                    col_groups[base] = []
                col_groups[base].append(col)
        
        for base, cols in col_groups.items():
            if len(cols) >= 4:
                # Check if numeric (not text)
                sample = df[cols[0]].dropna()
                if len(sample) > 0 and sample.dtype != 'object':
                    # IMPORTANT: Exclude binary/multi-select questions (0/1 or 1/2 values)
                    # These are checkbox questions, not rating scales
                    all_vals = set()
                    for col in cols:
                        try:
                            all_vals.update(df[col].dropna().astype(float).unique())
                        except:
                            pass
                    
                    is_binary = all_vals <= {0.0, 1.0, 2.0}
                    if is_binary:
                        continue  # Skip multi-select questions
                    
                    battery_groups.append({
                        'code': base,
                        'columns': sorted(cols),
                        'item_count': len(cols)
                    })
        
        if battery_groups:
            print(f"   Heuristic detection: {len(battery_groups)} rating batteries (excluding multi-select)")
            for bg in battery_groups:
                print(f"   - {bg['code']}: {bg['item_count']} items")
    
    results['battery_length'] = max([bg['item_count'] for bg in battery_groups]) if battery_groups else 0
    
    if battery_groups:
        straight_line_counts = {}
        
        for bg in battery_groups:
            cols = bg['columns']
            if len(cols) < 4:
                continue
            
            for idx, row in df.iterrows():
                resp_id = row[id_column]
                values = [row[col] for col in cols if pd.notna(row[col])]
                
                if len(values) >= 4 and len(set(values)) == 1:
                    if resp_id not in straight_line_counts:
                        straight_line_counts[resp_id] = 0
                    straight_line_counts[resp_id] += 1
        
        # Threshold: For short batteries (4-5 items), require straight-lining in 2+ batteries
        # For longer batteries (6+ items), 1 is enough
        # This reduces false positives from 4-item batteries where random agreement is common
        min_batteries_threshold = 2
        
        for resp_id, count in straight_line_counts.items():
            if count >= min_batteries_threshold:
                results['straight_liners'].append(resp_id)
        
        print(f"   Straight-liners found: {len(results['straight_liners'])} (threshold: {min_batteries_threshold}+ batteries)")
    else:
        print(f"   No batteries found for straight-lining check")
    
    # =========================================================================
    # 4. COMBINE RESULTS & RISK CLASSIFICATION
    # =========================================================================
    print(f"\n4. COMBINING RESULTS")
    
    speeders_set = set(results['speeders'])
    # Combine high and medium risk open-ended for the "suspicious_open" used in risk groups
    open_all_set = set(results['suspicious_open']) | set(results['suspicious_open_medium'])
    open_high_set = set(results['suspicious_open'])
    straight_set = set(results['straight_liners'])
    
    all_flagged = speeders_set | open_all_set | straight_set
    
    for resp_id in all_flagged:
        is_speeder = resp_id in speeders_set
        is_open = resp_id in open_all_set
        is_open_high = resp_id in open_high_set
        is_straight = resp_id in straight_set
        
        count = sum([is_speeder, is_open, is_straight])
        
        # Risk groups
        if is_speeder and is_open and is_straight:
            results['risk_groups']['all_three'].append(resp_id)
        elif is_speeder and is_open:
            results['risk_groups']['speeders_open'].append(resp_id)
        elif is_speeder and is_straight:
            results['risk_groups']['speeders_straight'].append(resp_id)
        elif is_open and is_straight:
            results['risk_groups']['open_straight'].append(resp_id)
        elif is_speeder:
            results['risk_groups']['speeders_only'].append(resp_id)
        elif is_open:
            results['risk_groups']['open_only'].append(resp_id)
        elif is_straight:
            results['risk_groups']['straight_only'].append(resp_id)
        
        # Recommendations
        if count >= 2 or is_open_high:
            results['recommendations']['high_risk'].append(resp_id)
        elif count == 1:
            results['recommendations']['medium_risk'].append(resp_id)
        else:
            results['recommendations']['low_risk'].append(resp_id)
    
    results['all_bad'] = list(all_flagged)
    
    # Summary
    print(f"\n{'=' * 80}")
    print(f"SUMMARY:")
    print(f"  Total respondents: {results['total_respondents']}")
    print(f"  Speeders: {len(results['speeders'])}")
    print(f"  Open-ended high risk: {len(results['suspicious_open'])}")
    print(f"  Open-ended medium risk: {len(results['suspicious_open_medium'])}")
    print(f"  Straight-liners: {len(results['straight_liners'])}")
    print(f"  Total flagged: {len(results['all_bad'])}")
    print(f"  HIGH RISK (recommend delete): {len(results['recommendations']['high_risk'])}")
    print(f"  MEDIUM RISK (consider delete): {len(results['recommendations']['medium_risk'])}")
    print(f"{'=' * 80}")
    
    return results, df


# =============================================================================
# SPSS SYNTAX GENERATION (for backward compat, also in spss_syntax_unified.py)
# =============================================================================

def generate_spss_syntax(results, id_column='ExternalId', output_file=None):
    """Generate SPSS syntax for deleting bad respondents."""
    lines = []
    lines.append(f"* Bad Respondents Detector v2.0 - SPSS Syntax.")
    lines.append(f"* Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.")
    lines.append(f"* Total respondents: {results['total_respondents']}.")
    lines.append(f"* Total flagged: {len(results['all_bad'])}.")
    lines.append(f"")
    
    # Variant 1: Delete all flagged
    lines.append(f"* === VARIANTA 1: Smazat VSE podezrele ({len(results['all_bad'])}) ===.")
    if results['all_bad']:
        id_list = " ".join([f"'{str(x)}'" if isinstance(x, str) else str(x) 
                           for x in results['all_bad']])
        lines.append(f"SELECT IF NOT ANY({id_column}, {id_list}).")
        lines.append(f"EXECUTE.")
    lines.append(f"")
    
    # Variant 2: Delete only high risk
    high_risk = results['recommendations']['high_risk']
    lines.append(f"* === VARIANTA 2: Smazat pouze VYSOKE RIZIKO ({len(high_risk)}) ===.")
    if high_risk:
        id_list = " ".join([f"'{str(x)}'" if isinstance(x, str) else str(x) 
                           for x in high_risk])
        lines.append(f"* SELECT IF NOT ANY({id_column}, {id_list}).")
        lines.append(f"* EXECUTE.")
    lines.append(f"")
    
    # Variant 3: Delete high + medium risk
    hm_risk = high_risk + results['recommendations']['medium_risk']
    lines.append(f"* === VARIANTA 3: Smazat VYSOKE + STREDNI RIZIKO ({len(hm_risk)}) ===.")
    if hm_risk:
        id_list = " ".join([f"'{str(x)}'" if isinstance(x, str) else str(x) 
                           for x in hm_risk])
        lines.append(f"* SELECT IF NOT ANY({id_column}, {id_list}).")
        lines.append(f"* EXECUTE.")
    
    syntax = "\n".join(lines)
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(syntax)
        print(f"\nSyntax saved to: {output_file}")
    
    return syntax

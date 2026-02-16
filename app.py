# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import tempfile
from datetime import datetime
import traceback
import sys

# Set UTF-8 encoding for prints
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Import our modules with error handling
try:
    from bad_respondents_detector import analyze_with_questionnaire
    from spss_syntax_unified import generate_spss_syntax_unified
    MODULES_LOADED = True
    print("✓ Modules loaded successfully")
except ImportError as e:
    print(f"✗ ERROR: Failed to import modules: {e}")
    MODULES_LOADED = False
except Exception as e:
    print(f"✗ ERROR loading modules: {e}")
    MODULES_LOADED = False

app = Flask(__name__, static_folder='static', static_url_path='')

# CORS configuration
CORS(app, resources={r"/*": {"origins": "*"}})

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()

ALLOWED_SAV = {'sav'}
ALLOWED_DOCX = {'docx'}

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

# Main page - serve frontend
@app.route('/')
def index():
    try:
        return send_from_directory('static', 'index.html')
    except Exception as e:
        return jsonify({'success': False, 'error': f'Chyba při načítání aplikace: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health():
    health_status = {
        'status': 'ok' if MODULES_LOADED else 'error',
        'message': 'Bad Respondents Detector v2.0 API running',
        'modules_loaded': MODULES_LOADED
    }
    return jsonify(health_status), 200 if MODULES_LOADED else 500

@app.route('/api/analyze', methods=['POST', 'OPTIONS'])
def analyze():
    if request.method == 'OPTIONS':
        return '', 204
    
    # Check if modules are loaded
    if not MODULES_LOADED:
        return jsonify({
            'success': False,
            'error': 'Server není správně nakonfigurován. Chybí potřebné moduly (pyreadstat, pandas, python-docx).'
        }), 500
    
    try:
        print("\n" + "="*80)
        print("NEW ANALYSIS REQUEST")
        print("="*80)
        
        # File validation
        if 'sav_file' not in request.files:
            return jsonify({'success': False, 'error': 'Chybí SAV soubor'}), 400
        
        if 'docx_file' not in request.files:
            return jsonify({'success': False, 'error': 'Chybí dotazník (.docx)'}), 400
        
        sav_file = request.files['sav_file']
        docx_file = request.files['docx_file']
        
        if sav_file.filename == '':
            return jsonify({'success': False, 'error': 'SAV soubor nebyl vybrán'}), 400
        
        if docx_file.filename == '':
            return jsonify({'success': False, 'error': 'Dotazník nebyl vybrán'}), 400
        
        if not allowed_file(sav_file.filename, ALLOWED_SAV):
            return jsonify({'success': False, 'error': 'SAV soubor musí mít příponu .sav'}), 400
        
        if not allowed_file(docx_file.filename, ALLOWED_DOCX):
            return jsonify({'success': False, 'error': 'Dotazník musí mít příponu .docx'}), 400
        
        # Save files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sav_filename = f"{timestamp}_{secure_filename(sav_file.filename)}"
        docx_filename = f"{timestamp}_{secure_filename(docx_file.filename)}"
        
        sav_path = os.path.join(app.config['UPLOAD_FOLDER'], sav_filename)
        docx_path = os.path.join(app.config['UPLOAD_FOLDER'], docx_filename)
        
        print(f"Saving files:")
        print(f"  SAV: {sav_path}")
        print(f"  DOCX: {docx_path}")
        
        sav_file.save(sav_path)
        docx_file.save(docx_path)
        
        print(f"Files saved successfully")
        
        # Analysis
        print(f"\nStarting analysis...")
        try:
            results, df = analyze_with_questionnaire(sav_path, docx_path)
            print(f"✓ Analysis completed successfully")
        except Exception as analysis_error:
            print(f"✗ Analysis failed: {str(analysis_error)}")
            print(traceback.format_exc())
            
            # Cleanup on error
            try:
                if os.path.exists(sav_path):
                    os.remove(sav_path)
                if os.path.exists(docx_path):
                    os.remove(docx_path)
            except:
                pass
            
            return jsonify({
                'success': False,
                'error': f'Chyba při analýze dat: {str(analysis_error)}'
            }), 500
        
        # Generate syntax
        print(f"\nGenerating SPSS syntax...")
        syntax_filename = f"delete_bad_{timestamp}.sps"
        syntax_path = os.path.join(app.config['UPLOAD_FOLDER'], syntax_filename)
        
        try:
            syntax = generate_spss_syntax_unified(
                results, 
                id_column=results['id_column'], 
                output_file=syntax_path
            )
            print(f"✓ Syntax generated: {syntax_path}")
        except Exception as syntax_error:
            print(f"✗ Syntax generation failed: {str(syntax_error)}")
            print(traceback.format_exc())
            return jsonify({
                'success': False,
                'error': f'Chyba při generování syntaxe: {str(syntax_error)}'
            }), 500
        
        # Build response
        response_data = {
            'success': True,
            'results': {
                'total_respondents': results['total_respondents'],
                'battery_length': results.get('battery_length', 'N/A'),
                'id_column': results['id_column'],
                'speeders': {
                    'count': len(results['speeders']),
                    'threshold_sec': results.get('speeder_threshold_sec', 0),
                    'threshold_min': results.get('speeder_threshold_min', 0)
                },
                'suspicious_open': {
                    'count': len(results['suspicious_open']) + len(results.get('suspicious_open_medium', [])),
                    'high_risk_count': len(results['suspicious_open']),
                    'medium_risk_count': len(results.get('suspicious_open_medium', []))
                },
                'straight_liners': {
                    'count': len(results['straight_liners'])
                },
                'risk_groups': {
                    'all_three': len(results['risk_groups']['all_three']),
                    'speeders_open': len(results['risk_groups']['speeders_open']),
                    'speeders_straight': len(results['risk_groups']['speeders_straight']),
                    'open_straight': len(results['risk_groups']['open_straight']),
                    'speeders_only': len(results['risk_groups']['speeders_only']),
                    'open_only': len(results['risk_groups']['open_only']),
                    'straight_only': len(results['risk_groups']['straight_only'])
                },
                'recommendations': {
                    'high_risk': len(results['recommendations']['high_risk']),
                    'medium_risk': len(results['recommendations']['medium_risk']),
                    'low_risk': len(results['recommendations']['low_risk'])
                },
                'total_bad': len(results['all_bad'])
            },
            'syntax_file': syntax_filename
        }
        
        print(f"\n✓ Response prepared successfully")
        print(f"  Total flagged: {len(results['all_bad'])}")
        print(f"  High risk: {len(results['recommendations']['high_risk'])}")
        print(f"  Medium risk: {len(results['recommendations']['medium_risk'])}")
        
        # Cleanup uploaded files (keep syntax file for download)
        try:
            if os.path.exists(sav_path):
                os.remove(sav_path)
            if os.path.exists(docx_path):
                os.remove(docx_path)
            print(f"✓ Cleanup completed")
        except Exception as cleanup_error:
            print(f"Warning: Cleanup failed: {cleanup_error}")
        
        print("="*80 + "\n")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {str(e)}")
        print(traceback.format_exc())
        print("="*80 + "\n")
        
        return jsonify({
            'success': False,
            'error': f'Neočekávaná chyba: {str(e)}'
        }), 500

@app.route('/api/download/<filename>', methods=['GET'])
def download(filename):
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
        
        if not os.path.exists(filepath):
            return jsonify({'success': False, 'error': 'Soubor nenalezen'}), 404
        
        response = send_file(
            filepath, 
            as_attachment=True,
            download_name=filename,
            mimetype='text/plain'
        )
        
        # Cleanup after download
        @response.call_on_close
        def cleanup():
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                    print(f"✓ Deleted syntax file: {filepath}")
            except Exception as e:
                print(f"Warning: Failed to delete {filepath}: {e}")
        
        return response
        
    except Exception as e:
        print(f"✗ Download error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': f'Chyba při stahování: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"\n{'='*80}")
    print(f"BAD RESPONDENTS DETECTOR v2.0")
    print(f"Port: {port}")
    print(f"Modules loaded: {MODULES_LOADED}")
    print(f"{'='*80}\n")
    
    app.run(host='0.0.0.0', port=port, debug=False)

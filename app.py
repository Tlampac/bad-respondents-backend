from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import tempfile
from datetime import datetime
import traceback

# Import our modules
from bad_respondents_detector import analyze_with_questionnaire
from spss_syntax_unified import generate_spss_syntax_unified

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
    return send_from_directory('static', 'index.html')

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'message': 'Bad Respondents Detector v2.0 API running'})

@app.route('/api/analyze', methods=['POST', 'OPTIONS'])
def analyze():
    if request.method == 'OPTIONS':
        return '', 204
        
    try:
        # File validation
        if 'sav_file' not in request.files:
            return jsonify({'error': 'Chybí SAV soubor'}), 400
        
        if 'docx_file' not in request.files:
            return jsonify({'error': 'Chybí dotazník (.docx)'}), 400
        
        sav_file = request.files['sav_file']
        docx_file = request.files['docx_file']
        
        if sav_file.filename == '':
            return jsonify({'error': 'SAV soubor nebyl vybrán'}), 400
        
        if docx_file.filename == '':
            return jsonify({'error': 'Dotazník nebyl vybrán'}), 400
        
        if not allowed_file(sav_file.filename, ALLOWED_SAV):
            return jsonify({'error': 'SAV soubor musí mít příponu .sav'}), 400
        
        if not allowed_file(docx_file.filename, ALLOWED_DOCX):
            return jsonify({'error': 'Dotazník musí mít příponu .docx'}), 400
        
        # Save files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sav_filename = f"{timestamp}_{secure_filename(sav_file.filename)}"
        docx_filename = f"{timestamp}_{secure_filename(docx_file.filename)}"
        
        sav_path = os.path.join(app.config['UPLOAD_FOLDER'], sav_filename)
        docx_path = os.path.join(app.config['UPLOAD_FOLDER'], docx_filename)
        
        sav_file.save(sav_path)
        docx_file.save(docx_path)
        
        print(f"Analyzing: {sav_path} with {docx_path}")
        
        # Analysis
        results, df = analyze_with_questionnaire(sav_path, docx_path)
        
        # Generate syntax
        syntax_filename = f"delete_bad_{timestamp}.sps"
        syntax_path = os.path.join(app.config['UPLOAD_FOLDER'], syntax_filename)
        
        syntax = generate_spss_syntax_unified(results, 
                                              id_column=results['id_column'], 
                                              output_file=syntax_path)
        
        # Return results as JSON
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
        
        # Cleanup
        try:
            os.remove(sav_path)
            os.remove(docx_path)
        except:
            pass
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': f'Chyba při analýze: {str(e)}'}), 500

@app.route('/api/download/<filename>', methods=['GET'])
def download(filename):
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'Soubor nenalezen'}), 404
        
        response = send_file(filepath, 
                           as_attachment=True,
                           download_name=filename,
                           mimetype='text/plain')
        
        # Cleanup after download
        @response.call_on_close
        def cleanup():
            try:
                os.remove(filepath)
            except:
                pass
        
        return response
        
    except Exception as e:
        print(f"Download error: {str(e)}")
        return jsonify({'error': f'Chyba při stahování: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

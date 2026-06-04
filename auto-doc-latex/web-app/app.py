"""
ITU-T Report Generator - Flask Application
"""

from flask import Flask, render_template, request, send_file, jsonify
import os
import sys
import shutil
import glob

# Add web-app directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import active_config, ensure_directories, TEMP_DIR
from utils import (
    create_temp_directory,
    create_zip,
    cleanup_old_files,
    cleanup_all_temp_files,
    generate_wp_report,
    generate_question_report,
    validate_wp_config,
    validate_question_config
)


def cleanup_previous_reports(report_prefix):
    """
    Delete previous reports matching the given prefix pattern.

    Args:
        report_prefix: Pattern like 'report-SG17-WP1' or 'report-SG17-Q10'
    """
    if not os.path.exists(TEMP_DIR):
        return

    for item in os.listdir(TEMP_DIR):
        item_path = os.path.join(TEMP_DIR, item)
        if not os.path.isdir(item_path):
            continue

        for zip_file in glob.glob(os.path.join(item_path, f'{report_prefix}-*.zip')):
            try:
                shutil.rmtree(item_path)
                break
            except (PermissionError, OSError) as e:
                print(f"Warning: Could not delete {item_path}: {e}")


def build_zip_filename(report_type, config_data):
    """
    Build a descriptive ZIP filename.

    Args:
        report_type: 'wp' or 'question'
        config_data: Configuration dictionary with group, workingParty/question, start, end

    Returns:
        Tuple of (filename, prefix for cleanup)
        Example: ('report-SG17-WP1-03-11-12-2025.zip', 'report-SG17-WP1')
    """
    group = config_data.get('group', 17)
    start = config_data.get('start', '').replace('/', '-')

    start_parts = start.split('-') if start else ['2025', '01', '01']
    start_day = start_parts[2] if len(start_parts) > 2 else '01'
    start_month = start_parts[1] if len(start_parts) > 1 else '01'
    start_year = start_parts[0] if start_parts else '2025'

    date_part = f"{start_day}-{start_month}-{start_year}"

    if report_type == 'wp':
        wp = config_data.get('workingParty', 1)
        prefix = f"report-SG{group}-WP{wp}"
    else:
        question = config_data.get('question', 1)
        prefix = f"report-SG{group}-Q{question}"

    return f"{prefix}-{date_part}.zip", prefix

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(active_config)

# Ensure required directories exist
ensure_directories()

# Cleanup all temp files on startup
cleanup_all_temp_files()


# ============================================
# Routes
# ============================================

@app.route('/')
def index():
    """Render the main page with the form"""
    return render_template('index.html')


@app.route('/api/generate-wp-report', methods=['POST'])
def api_generate_wp_report():
    """
    Generate a Working Party report from JSON data

    Expected JSON format:
    {
        "group": 17,
        "workingParty": 1,
        "place": "Geneva",
        "start": "2025/12/03",
        "end": "2025/12/11",
        "sessions": 1,
        "meetingDays": ["2025/12/10"],
        "documentType": "report"
    }

    Returns:
        JSON with download_id on success, or error message
    """
    try:
        # Get JSON data from request
        config_data = request.json

        # Validate the configuration
        errors = validate_wp_config(config_data)
        if errors:
            return jsonify({
                'success': False,
                'error': '; '.join(errors)
            }), 400

        # Build descriptive filename and cleanup previous reports
        zip_filename, prefix = build_zip_filename('wp', config_data)
        cleanup_previous_reports(prefix)

        # Create temporary directory
        temp_dir = create_temp_directory()
        download_id = os.path.basename(temp_dir)

        # Generate the report
        template_path = generate_wp_report(config_data, temp_dir)

        # Create full ZIP file
        zip_path = os.path.join(temp_dir, zip_filename)
        create_zip(template_path, zip_path)

        # Create variables-only ZIP file
        variables_path = os.path.join(template_path, 'chapters', 'variables')
        variables_zip_filename = zip_filename.replace('.zip', '-variables.zip')
        variables_zip_path = os.path.join(temp_dir, variables_zip_filename)
        create_zip(variables_path, variables_zip_path)

        # Return download ID
        return jsonify({
            'success': True,
            'download_id': download_id,
            'filename': zip_filename,
            'variables_filename': variables_zip_filename
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/generate-question-report', methods=['POST'])
def api_generate_question_report():
    """
    Generate a Question report from JSON data

    Expected JSON format:
    {
        "group": 17,
        "question": 10,
        "place": "Geneva",
        "start": "2025/04/08",
        "end": "2025/04/17",
        "documentType": "report"
    }

    Returns:
        JSON with download_id on success, or error message
    """
    try:
        # Get JSON data from request
        config_data = request.json

        # Validate the configuration
        errors = validate_question_config(config_data)
        if errors:
            return jsonify({
                'success': False,
                'error': '; '.join(errors)
            }), 400

        # Build descriptive filename and cleanup previous reports
        zip_filename, prefix = build_zip_filename('question', config_data)
        cleanup_previous_reports(prefix)

        # Create temporary directory
        temp_dir = create_temp_directory()
        download_id = os.path.basename(temp_dir)

        # Generate the report
        template_path = generate_question_report(config_data, temp_dir)

        # Create full ZIP file
        zip_path = os.path.join(temp_dir, zip_filename)
        create_zip(template_path, zip_path)

        # Create variables-only ZIP file
        variables_path = os.path.join(template_path, 'chapters', 'variables')
        variables_zip_filename = zip_filename.replace('.zip', '-variables.zip')
        variables_zip_path = os.path.join(temp_dir, variables_zip_filename)
        create_zip(variables_path, variables_zip_path)

        # Return download ID
        return jsonify({
            'success': True,
            'download_id': download_id,
            'filename': zip_filename,
            'variables_filename': variables_zip_filename
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/download/<download_id>')
def api_download(download_id):
    """
    Download the generated full ZIP file

    Args:
        download_id: Timestamp ID (e.g., '20251226_153045')

    Returns:
        ZIP file for download
    """
    try:
        # Find the ZIP file in temp directory
        temp_dir_path = os.path.join(
            os.path.dirname(__file__), 'temp', download_id
        )

        # Check if directory exists
        if not os.path.exists(temp_dir_path):
            return jsonify({
                'success': False,
                'error': 'Download not found or expired'
            }), 404

        # List ZIP files excluding variables-only
        zip_files = [f for f in os.listdir(temp_dir_path)
                     if f.endswith('.zip') and '-variables.zip' not in f]

        if not zip_files:
            return jsonify({
                'success': False,
                'error': 'ZIP file not found'
            }), 404

        # Get the first ZIP file
        zip_path = os.path.join(temp_dir_path, zip_files[0])

        # Send file for download
        return send_file(
            zip_path,
            as_attachment=True,
            download_name=zip_files[0]
        )

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/download/<download_id>/variables')
def api_download_variables(download_id):
    """
    Download only the variables folder as ZIP

    Args:
        download_id: Timestamp ID (e.g., '20251226_153045')

    Returns:
        ZIP file for download (variables only)
    """
    try:
        # Find the ZIP file in temp directory
        temp_dir_path = os.path.join(
            os.path.dirname(__file__), 'temp', download_id
        )

        # Check if directory exists
        if not os.path.exists(temp_dir_path):
            return jsonify({
                'success': False,
                'error': 'Download not found or expired'
            }), 404

        # List variables ZIP files
        zip_files = [f for f in os.listdir(temp_dir_path)
                     if f.endswith('-variables.zip')]

        if not zip_files:
            return jsonify({
                'success': False,
                'error': 'Variables ZIP file not found'
            }), 404

        # Get the first ZIP file
        zip_path = os.path.join(temp_dir_path, zip_files[0])

        # Send file for download
        return send_file(
            zip_path,
            as_attachment=True,
            download_name=zip_files[0]
        )

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# Error Handlers
# ============================================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'success': False,
        'error': 'Not found'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500


# ============================================
# Main
# ============================================

if __name__ == '__main__':
    # Run the Flask development server
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=True
    )

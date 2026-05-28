"""
Report generation wrapper for existing scripts
"""

import json
import sys
import os
import shutil
from config import SCRIPTS_DIR, WP_TEMPLATE_DIR, QUESTION_TEMPLATE_DIR
from utils.file_handler import copy_template


def generate_wp_report(config_dict, output_dir):
    """
    Generate a Working Party report

    Args:
        config_dict (dict): Configuration data from web form
        output_dir (str): Directory where to generate the report

    Returns:
        str: Path to the generated template directory
    """
    # Copy template to output directory
    template_copy = copy_template('wp', output_dir)

    # Add documentType required by backend script
    config_with_type = config_dict.copy()
    config_with_type['documentType'] = 'report'

    # Create JSON config file
    config_path = os.path.join(output_dir, 'config.json')
    with open(config_path, 'w') as f:
        json.dump(config_with_type, f, indent=2)

    # Clean the results directory in the original template
    # (backend script writes there, so we need it empty before each run)
    original_results = os.path.join(WP_TEMPLATE_DIR, 'chapters', 'variables')
    if os.path.exists(original_results):
        # Delete all files in the directory
        for item in os.listdir(original_results):
            item_path = os.path.join(original_results, item)
            try:
                if os.path.isfile(item_path) or os.path.islink(item_path):
                    os.unlink(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            except Exception as e:
                print(f'Warning: Failed to delete {item_path}: {e}')
    else:
        os.makedirs(original_results)

    # Add scripts-new to Python path
    sys.path.insert(0, SCRIPTS_DIR)

    # Run the existing script
    original_argv = sys.argv
    sys.argv = ['generate_wp_report.py', config_path]

    try:
        from generate_wp_report import main
        main()
    finally:
        sys.argv = original_argv

    # Copy generated results from original template to our copy
    copy_results = os.path.join(template_copy, 'chapters', 'variables')

    # Copy the generated files (dirs_exist_ok handles if directory exists)
    shutil.copytree(original_results, copy_results, dirs_exist_ok=True)

    return template_copy


def generate_question_report(config_dict, output_dir):
    """
    Generate a Question report

    Args:
        config_dict (dict): Configuration data from web form
        output_dir (str): Directory where to generate the report

    Returns:
        str: Path to the generated template directory
    """
    # Copy template to output directory
    template_copy = copy_template('question', output_dir)

    # Add documentType required by backend script
    config_with_type = config_dict.copy()
    config_with_type['documentType'] = 'report'

    # Create JSON config file
    config_path = os.path.join(output_dir, 'config.json')
    with open(config_path, 'w') as f:
        json.dump(config_with_type, f, indent=2)

    # Clean the results directory in the original template
    # (backend script writes there, so we need it empty before each run)
    original_results = os.path.join(QUESTION_TEMPLATE_DIR, 'chapters', 'variables')
    if os.path.exists(original_results):
        # Delete all files in the directory
        for item in os.listdir(original_results):
            item_path = os.path.join(original_results, item)
            try:
                if os.path.isfile(item_path) or os.path.islink(item_path):
                    os.unlink(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            except Exception as e:
                print(f'Warning: Failed to delete {item_path}: {e}')
    else:
        os.makedirs(original_results)

    # Add scripts-new to Python path
    sys.path.insert(0, SCRIPTS_DIR)

    # Run the existing script
    original_argv = sys.argv
    sys.argv = ['generate_question_report.py', config_path]

    try:
        from generate_question_report import main
        main()
    finally:
        sys.argv = original_argv

    # Copy generated results from original template to our copy
    copy_results = os.path.join(template_copy, 'chapters', 'variables')

    # Copy the generated files (dirs_exist_ok handles if directory exists)
    shutil.copytree(original_results, copy_results, dirs_exist_ok=True)

    return template_copy

"""
File handling utilities for ITU-T Report Generator
"""

import os
import shutil
import zipfile
from datetime import datetime
from config import TEMP_DIR, WP_TEMPLATE_DIR, QUESTION_TEMPLATE_DIR


def create_temp_directory():
    """
    Create a unique temporary directory with timestamp

    Returns:
        str: Path to the created directory
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    temp_path = os.path.join(TEMP_DIR, timestamp)
    os.makedirs(temp_path, exist_ok=True)
    return temp_path


def create_zip(source_dir, output_zip):
    """
    Compress a directory into a ZIP file

    Args:
        source_dir (str): Directory to compress
        output_zip (str): Path for the output ZIP file

    Returns:
        str: Path to the created ZIP file
    """
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, os.path.dirname(source_dir))
                zipf.write(file_path, arcname)
    return output_zip


def cleanup_all_temp_files():
    """
    Delete all temporary files in the temp directory.
    Called on application startup.
    """
    if not os.path.exists(TEMP_DIR):
        return

    for item in os.listdir(TEMP_DIR):
        item_path = os.path.join(TEMP_DIR, item)
        try:
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
        except (PermissionError, OSError) as e:
            print(f"Warning: Could not delete {item_path}: {e}")


def cleanup_old_files(max_age_hours=1):
    """
    Delete temporary files older than max_age_hours

    Args:
        max_age_hours (int): Maximum age in hours before deletion
    """
    if not os.path.exists(TEMP_DIR):
        return

    now = datetime.now()

    for item in os.listdir(TEMP_DIR):
        item_path = os.path.join(TEMP_DIR, item)

        if not os.path.isdir(item_path):
            continue

        creation_time = datetime.fromtimestamp(os.path.getctime(item_path))
        age = now - creation_time

        if age.total_seconds() > max_age_hours * 3600:
            try:
                shutil.rmtree(item_path)
            except (PermissionError, OSError) as e:
                # Ignore permission errors (file might be in use)
                print(f"Warning: Could not delete {item_path}: {e}")


def copy_template(template_type, destination_dir):
    """
    Copy template directory to destination

    Args:
        template_type (str): 'wp' or 'question'
        destination_dir (str): Destination directory path

    Returns:
        str: Path to the copied template directory
    """
    if template_type == 'wp':
        source = WP_TEMPLATE_DIR
        template_name = 'wp_doc_template'
    elif template_type == 'question':
        source = QUESTION_TEMPLATE_DIR
        template_name = 'question_doc_template'
    else:
        raise ValueError(f"Invalid template_type: {template_type}")

    dest = os.path.join(destination_dir, template_name)
    shutil.copytree(source, dest)

    # Remove the variables directory from the copied template
    # (it will be populated later with generated files)
    results_dir = os.path.join(dest, 'chapters', 'variables')
    if os.path.exists(results_dir):
        # Delete all files inside results/ instead of removing the directory
        # (avoids Windows permission issues)
        for item in os.listdir(results_dir):
            item_path = os.path.join(results_dir, item)
            try:
                if os.path.isfile(item_path) or os.path.islink(item_path):
                    os.unlink(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            except Exception as e:
                print(f'Warning: Failed to delete {item_path}: {e}')

    return dest

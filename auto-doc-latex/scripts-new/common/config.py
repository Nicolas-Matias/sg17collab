"""JSON configuration loader for ITU document generation."""

import json
import os
import sys
import datetime


def load_config(config_path):
    """Load and validate a JSON configuration file.

    Returns a dict with all configuration values, with defaults applied.
    Relative paths (e.g. workProgramme) are resolved relative to the
    config file's directory.
    """
    try:
        with open(config_path, "r", encoding="utf-8") as fid:
            content = json.loads(fid.read())
    except Exception as e:
        print(f"Error loading config {config_path}: {e}")
        sys.exit(1)

    # Document type
    doc_type = content.get('documentType')
    if doc_type not in ("agenda", "report"):
        print(f"Unknown document type: {doc_type}")
        sys.exit(1)

    # Study group
    group = _get_int(content, 'group', "group")

    # Start/end dates
    start_string = content.get('start')
    start = _parse_date(start_string, "start date")
    start_date = f"{start.year:04}{start.month:02}{start.day:02}"

    end_string = content.get('end')
    end = _parse_date(end_string, "end date") if end_string else None

    # Place
    place = content.get('place', '')

    config = {
        'documentType': doc_type,
        'group': group,
        'place': place,
        'start': start,
        'startString': start_string,
        'startDate': start_date,
        'end': end,
        '_raw': content,
    }

    return config


def load_question_config(config_path):
    """Load config for a Question report. Adds the 'question' field."""
    config = load_config(config_path)
    config['question'] = _get_int(config['_raw'], 'question', "question")
    return config


def load_wp_config(config_path):
    """Load config for a Working Party report. Adds the 'workingParty' field."""
    config = load_config(config_path)
    config['workingParty'] = _get_int(config['_raw'], 'workingParty', "workingParty")

    # Resolve workProgramme CSV path relative to config file directory
    wp_csv = config['_raw'].get('workProgramme', '')
    if wp_csv and not os.path.isabs(wp_csv):
        config_dir = os.path.dirname(os.path.abspath(config_path))
        wp_csv = os.path.join(config_dir, wp_csv)
    config['workProgramme'] = wp_csv

    # Introduction fields
    config['sessions'] = config['_raw'].get('sessions')
    meeting_days = config['_raw'].get('meetingDays') or []
    config['meetingDays'] = [_parse_date(d, "meetingDays entry") for d in meeting_days]

    return config


def _get_int(content, key, label):
    """Extract an integer value from config."""
    val = content.get(key)
    if val is None:
        print(f"Missing required field: {label}")
        sys.exit(1)
    try:
        return int(val)
    except (ValueError, TypeError):
        print(f"Invalid {label}: {val}")
        sys.exit(1)




def _parse_date(date_string, label):
    """Parse a YYYY/MM/DD date string."""
    try:
        return datetime.datetime.strptime(date_string, "%Y/%m/%d")
    except Exception:
        print(f"Invalid {label}: {date_string}")
        sys.exit(1)

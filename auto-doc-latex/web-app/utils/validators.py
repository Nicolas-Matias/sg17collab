"""
Input validation utilities
"""

from datetime import datetime


def validate_date_format(date_string):
    """
    Validate date format (YYYY/MM/DD)

    Args:
        date_string (str): Date in format YYYY/MM/DD

    Returns:
        tuple: (is_valid, error_message, datetime_object)
    """
    if not date_string:
        return False, "Date is required", None

    try:
        dt = datetime.strptime(date_string, '%Y/%m/%d')
        return True, None, dt
    except ValueError:
        return False, f"Invalid date format: {date_string} (expected YYYY/MM/DD)", None


def validate_dates(start, end):
    """
    Validate start and end dates

    Args:
        start (str): Start date (YYYY/MM/DD)
        end (str): End date (YYYY/MM/DD)

    Returns:
        tuple: (is_valid, error_message)
    """
    # Validate start date
    valid_start, error_start, dt_start = validate_date_format(start)
    if not valid_start:
        return False, error_start

    # Validate end date
    valid_end, error_end, dt_end = validate_date_format(end)
    if not valid_end:
        return False, error_end

    # Check start < end
    if dt_start >= dt_end:
        return False, f"Start date ({start}) must be before end date ({end})"

    return True, None


def validate_study_group(group):
    """
    Validate study group number

    Args:
        group (int or str): Study group number

    Returns:
        tuple: (is_valid, error_message)
    """
    if group is None or group == '':
        return False, "Study group is required"

    try:
        group_num = int(group)
        if group_num <= 0:
            return False, f"Study group must be positive (got {group_num})"
        return True, None
    except (ValueError, TypeError):
        return False, f"Invalid study group: {group}"


def validate_working_party(wp):
    """
    Validate working party number

    Args:
        wp (int or str): Working party number

    Returns:
        tuple: (is_valid, error_message)
    """
    if wp is None or wp == '':
        return False, "Working party is required"

    try:
        wp_num = int(wp)
        if wp_num <= 0:
            return False, f"Working party must be positive (got {wp_num})"
        return True, None
    except (ValueError, TypeError):
        return False, f"Invalid working party: {wp}"


def validate_question(question):
    """
    Validate question number

    Args:
        question (int or str): Question number

    Returns:
        tuple: (is_valid, error_message)
    """
    if question is None or question == '':
        return False, "Question is required"

    try:
        q_num = int(question)
        if q_num <= 0:
            return False, f"Question must be positive (got {q_num})"
        return True, None
    except (ValueError, TypeError):
        return False, f"Invalid question: {question}"


def validate_wp_config(config):
    """
    Validate Working Party configuration

    Args:
        config (dict): Configuration dictionary

    Returns:
        list: List of error messages (empty if valid)
    """
    errors = []

    # Validate study group
    valid, error = validate_study_group(config.get('group'))
    if not valid:
        errors.append(error)

    # Validate working party
    valid, error = validate_working_party(config.get('workingParty'))
    if not valid:
        errors.append(error)

    # Validate dates
    valid, error = validate_dates(config.get('start'), config.get('end'))
    if not valid:
        errors.append(error)

    # Validate place
    if not config.get('place') or not config.get('place').strip():
        errors.append("Place is required")

    return errors


def validate_question_config(config):
    """
    Validate Question configuration

    Args:
        config (dict): Configuration dictionary

    Returns:
        list: List of error messages (empty if valid)
    """
    errors = []

    # Validate study group
    valid, error = validate_study_group(config.get('group'))
    if not valid:
        errors.append(error)

    # Validate question
    valid, error = validate_question(config.get('question'))
    if not valid:
        errors.append(error)

    # Validate dates
    valid, error = validate_dates(config.get('start'), config.get('end'))
    if not valid:
        errors.append(error)

    # Validate place
    if not config.get('place') or not config.get('place').strip():
        errors.append("Place is required")

    return errors


def sanitize_string(text):
    """
    Basic string sanitization

    Args:
        text (str): Input string

    Returns:
        str: Sanitized string
    """
    if not text:
        return ""

    # Remove leading/trailing whitespace
    text = text.strip()

    # Remove potentially dangerous characters (basic protection)
    # Note: This is basic sanitization, not full XSS protection
    dangerous_chars = ['<', '>', ';', '&', '|', '$', '`']
    for char in dangerous_chars:
        text = text.replace(char, '')

    return text

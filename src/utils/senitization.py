

import json


def tojson_filter(obj):
    return json.dumps(obj)

def sanitize_for_excel(value):
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    sanitized = ''.join(char for char in value if ord(char) >= 32 or char in '\t\n\r')
    if not sanitized.strip() and value:
        return "[Binary/Illegal characters removed]"
    return sanitized
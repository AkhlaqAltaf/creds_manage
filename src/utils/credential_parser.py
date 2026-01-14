"""
Credential parsing utilities
"""
from typing import Optional, List, Tuple
from urllib.parse import urlparse


def parse_multi_line_credential_block(lines: List[str], start_idx: int) -> Optional[Tuple[tuple, int]]:
    """
    Parse a multi-line credential block in format:
    SEARCH -> domain
    URL -> url
    LOGIN -> user
    PASSWORD -> password
    ===============
    
    Args:
        lines: List of all lines in the file
        start_idx: Starting index to look for the block
        
    Returns:
        Tuple of ((url, user, password), end_idx) or None if parsing fails
        end_idx is the index after the separator line
    """
    if start_idx >= len(lines):
        return None
    
    # Look for SEARCH, URL, LOGIN, PASSWORD pattern
    search_line = None
    url_line = None
    login_line = None
    password_line = None
    separator_idx = None
    
    i = start_idx
    while i < len(lines) and i < start_idx + 10:  # Look ahead max 10 lines
        line = lines[i].strip()
        
        # Skip empty lines
        if not line:
            i += 1
            continue
        
        if line.startswith('SEARCH ->'):
            search_line = line
        elif line.startswith('URL ->'):
            url_line = line
        elif line.startswith('LOGIN ->'):
            login_line = line
        elif line.startswith('PASSWORD ->'):
            password_line = line
        elif line.startswith('===============') or line.startswith('===') or line == '=':
            separator_idx = i
            break
        
        i += 1
    
    # Need at least URL, LOGIN, and PASSWORD
    if not (url_line and login_line and password_line):
        return None
    
    # Extract values
    try:
        url = url_line.split('->', 1)[1].strip() if '->' in url_line else None
        user = login_line.split('->', 1)[1].strip() if '->' in login_line else None
        password = password_line.split('->', 1)[1].strip() if '->' in password_line else None
        
        # Validate
        if not url or not user or not password:
            return None
        
        # Skip if password is "EMPTY" or empty
        if password.upper() == 'EMPTY' or not password or password.strip() == '':
            return None
        
        # Skip if URL looks invalid (just protocol or empty)
        if not url or url.strip() == '' or url.lower() in ('http://', 'https://'):
            return None
        
        # Skip if user is empty
        if not user or user.strip() == '':
            return None
        
        # Ensure URL has protocol
        if url and not url.startswith(('http://', 'https://')):
            url = f'https://{url}'
        
        # Return the credential tuple and the index after separator (or next line)
        end_idx = separator_idx + 1 if separator_idx is not None else i
        return ((url, user, password), end_idx)
    except Exception:
        return None


def parse_credential_line(line: str) -> Optional[tuple]:
    """
    Parse a credential line, return (url, user, password) or None
    
    Supports two formats:
    1. Single line: url:user:password
    2. Multi-line block format (returns None, should use parse_multi_line_credential_block)
    
    Args:
        line: A line from credential file in format: url:user:password
        
    Returns:
        Tuple of (url, user, password) or None if parsing fails
    """
    line = line.strip()
    if not line:
        return None
    
    # Skip multi-line format markers
    if line.startswith(('SEARCH ->', 'URL ->', 'LOGIN ->', 'PASSWORD ->', '===============')):
        return None
    
    # More robust parsing that handles passwords with colons
    # First, try to find the protocol to identify the URL part
    if line.startswith('http://'):
        protocol_end = 7
    elif line.startswith('https://'):
        protocol_end = 8
    else:
        # If no protocol, we'll try to split from the right
        parts = line.rsplit(':', 2)
        if len(parts) == 3:
            url, user, password = parts
            url = url.strip()
            user = user.strip()
            password = password.strip()
            
            if url and user and password:
                # Add protocol if missing
                if not url.startswith(('http://', 'https://')):
                    url = f'https://{url}'
                return (url, user, password)
        return None
    
    # For URLs with protocol, find the first colon after the protocol
    # and the last two colons for user:password
    url_part = line
    
    # Find the position after protocol
    after_protocol = line[protocol_end:]
    
    # Split into two parts: everything before last 2 colons and the user:password part
    last_colon_index = url_part.rfind(':')
    if last_colon_index == -1:
        return None
    
    # Find the second last colon
    second_last_colon_index = url_part.rfind(':', 0, last_colon_index)
    if second_last_colon_index == -1:
        return None
    
    # Extract parts
    url = line[:second_last_colon_index].strip()
    user_password_part = line[second_last_colon_index + 1:]
    
    # Split user and password
    user_password_parts = user_password_part.split(':', 1)
    if len(user_password_parts) != 2:
        return None
    
    user, password = user_password_parts
    user = user.strip()
    password = password.strip()
    
    if not url or not user or not password:
        return None
    
    return (url, user, password)


def extract_domain(url: str) -> Optional[str]:
    """
    Extract domain from URL
    
    Args:
        url: URL string
        
    Returns:
        Domain string or None if extraction fails
    """
    try:
        if not url or not isinstance(url, str):
            return None
        
        url = url.strip()
        if not url:
            return None
        
        # Skip if it's just a protocol
        if url.lower() in ('http://', 'https://', 'http:', 'https:'):
            return None
        
        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            url = f'https://{url}'
        
        parsed = urlparse(url)
        domain_str = parsed.netloc or parsed.path.split('/')[0]
        
        if domain_str:
            domain_str = domain_str.lower().strip()
            
            # Filter out invalid domains
            # Skip if it's just a protocol or empty
            if not domain_str or domain_str in ('http:', 'https:', 'http://', 'https://'):
                return None
            
            # Skip if it doesn't look like a valid domain (no dots or just numbers/special chars)
            if '.' not in domain_str or len(domain_str) < 3:
                return None
            
            # Remove port if present
            if ':' in domain_str:
                domain_str = domain_str.split(':')[0]
            
            # Basic validation - should have at least one dot and be alphanumeric with dots and hyphens
            if not all(c.isalnum() or c in '.-' for c in domain_str):
                return None
            
            return domain_str
    except Exception:
        pass
    return None


import os

def update_env_file(updates: dict, env_path: str = None):
    """
    Updates or adds keys in the .env file without removing existing ones.
    """
    if env_path is None:
        # Default to root .env (assuming this is called from backend/)
        env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
    
    lines = []
    if os.path.isfile(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

    # Create a map of existing keys to line numbers
    key_line_map = {}
    for idx, line in enumerate(lines):
        if line.strip() and not line.startswith('#') and '=' in line:
            key = line.split('=', 1)[0].strip()
            key_line_map[key] = idx

    for key, value in updates.items():
        line_content = f"{key}={value}\n"
        if key in key_line_map:
            lines[key_line_map[key]] = line_content
        else:
            if lines and not lines[-1].endswith('\n'):
                lines[-1] += '\n'
            lines.append(line_content)
            key_line_map[key] = len(lines) - 1

    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
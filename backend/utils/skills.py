
SKILL_SYNONYMS = {
    'ai': ['artificial intelligence'],
    'artificial intelligence': ['ai'],
    'ml': ['machine learning'],
    'machine learning': ['ml'],
    'ds': ['data science'],
    'data science': ['ds'],
    'web dev': ['web development'],
    'web development': ['web dev'],
    'app dev': ['app development', 'mobile app development'],
    'app development': ['app dev'],
    'js': ['javascript'],
    'javascript': ['js'],
    'ts': ['typescript'],
    'typescript': ['ts'],
    'cpp': ['c++'],
    'c++': ['cpp'],
    'react': ['reactjs', 'react.js'],
    'reactjs': ['react'],
    'node': ['nodejs', 'node.js'],
    'nodejs': ['node'],
    'ui/ux': ['user interface', 'user experience', 'ui', 'ux'],
    'ui': ['ui/ux', 'user interface'],
    'ux': ['ui/ux', 'user experience'],
    'py': ['python'],
    'python': ['py']
}

def expand_skills(skills_list):
    """
    Takes a list of skills and returns a list containing the original skills
    plus any known synonyms/expansions.
    """
    expanded = set()
    for skill in skills_list:
        if not skill:
            continue
        s_lower = skill.strip().lower()
        expanded.add(s_lower)
        
        # Add synonyms if they exist
        if s_lower in SKILL_SYNONYMS:
            expanded.update(SKILL_SYNONYMS[s_lower])
            
    return list(expanded)

def all_known_terms():
    base = set()
    for k, vs in SKILL_SYNONYMS.items():
        base.add(k.strip().lower())
        for v in vs:
            base.add(v.strip().lower())
    return base

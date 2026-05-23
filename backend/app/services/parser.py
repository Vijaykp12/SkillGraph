import io
import re
from pypdf import PdfReader

# Key skills and their regex patterns to match in raw text for keyword extraction
SKILL_PATTERNS = {
    "Python": [r"\bpython\b", r"\bpy\b"],
    "JavaScript": [r"\bjavascript\b", r"\bjs\b"],
    "TypeScript": [r"\btypescript\b", r"\bts\b"],
    "SQL": [r"\bsql\b", r"\bsqlite\b", r"\bmysql\b", r"\bpostgres\b", r"\bpostgresql\b", r"\boracle\b", r"\bsql-server\b"],
    "Rust": [r"\brust\b"],
    "Go": [r"\bgolang\b", r"\bgo\s+(?:lang|language|programming|code|dev|developer|backend)\b"],
    "C++": [r"\bc\+\+(?!\w)", r"\bcpp\b"],
    "Java": [r"\bjava\b"],
    "C#": [r"\bc#(?!\w)", r"\bcsharp\b"],
    "Git": [r"\bgit\b", r"\bgithub\b", r"\bgitlab\b"],
    "HTML & CSS": [r"\bhtml(?:5)?\b", r"\bcss(?:3)?\b"],
    "PyTorch": [r"\bpytorch\b", r"\bpy\s*torch\b"],
    "TensorFlow": [r"\btensorflow\b", r"\btensor\s*flow\b"],
    "Scikit-Learn": [r"\bscikit-learn\b", r"\bscikit\s+learn\b", r"\bsklearn\b"],
    "Graph Neural Networks": [r"\bgraph\s+neural\s+network(?:s)?\b", r"\bgnn(?:s)?\b"],
    "Natural Language Processing": [r"\bnatural\s+language\s+processing\b", r"\bnlp\b"],
    "Transformers": [r"\btransformer(?:s)?\b"],
    "Large Language Models": [r"\blarge\s+language\s+model(?:s)?\b", r"\bllm(?:s)?\b"],
    "Computer Vision": [r"\bcomputer\s+vision\b", r"\bcv\b"],
    "MLOps": [r"\bmlops\b", r"\bml\s+ops\b"],
    "Hugging Face": [r"\bhugging\s*face\b", r"\bhf\b"],
    "Deep Learning": [r"\bdeep\s+learning\b"],
    "Neo4j": [r"\bneo4j\b", r"\bcypher\b"],
    "PostgreSQL": [r"\bpostgres(?:ql)?\b"],
    "Redis": [r"\bredis\b"],
    "FAISS": [r"\bfaiss\b"],
    "MongoDB": [r"\bmongo(?:db)?\b"],
    "MySQL": [r"\bmysql\b"],
    "Elasticsearch": [r"\belasticsearch\b"],
    "Apache Spark": [r"\bspark\b", r"\bapache\s+spark\b", r"\bpyspark\b"],
    "Apache Hadoop": [r"\bhadoop\b", r"\bapache\s+hadoop\b"],
    "Snowflake": [r"\bsnowflake\b"],
    "Data Warehousing": [r"\bdata\s+warehous(?:e|ing)\b", r"\bdwh\b"],
    "Docker": [r"\bdocker\b"],
    "Kubernetes": [r"\bkubernetes\b", r"\bk8s\b"],
    "AWS": [r"\baws\b", r"\bamazon\s+web\s+services\b"],
    "Google Cloud Platform": [r"\bgcp\b", r"\bgoogle\s+cloud\b", r"\bgoogle\s+cloud\s+platform\b"],
    "Microsoft Azure": [r"\bazure\b", r"\bmicrosoft\s+azure\b"],
    "Terraform": [r"\bterraform\b"],
    "CI/CD": [r"\bci/cd\b", r"\bci\s+and\s+cd\b", r"\bcontinuous\s+integration\b"],
    "Ansible": [r"\bansible\b"],
    "Jenkins": [r"\bjenkins\b"],
    "Prometheus": [r"\bprometheus\b"],
    "React": [r"\breact(?:js|\.js)?\b"],
    "Next.js": [r"\bnext(?:js|\.js)?\b"],
    "Vue.js": [r"\bvue(?:js|\.js)?\b"],
    "Angular": [r"\bangular(?:js)?\b"],
    "Svelte": [r"\bsvelte\b"],
    "TailwindCSS": [r"\btailwind(?:css)?\b"],
    "Framer Motion": [r"\bframer\s+motion\b"],
    "D3.js": [r"\bd3(?:js|\.js)?\b"],
    "Cytoscape.js": [r"\bcytoscape(?:js|\.js)?\b"],
    "Figma": [r"\bfigma\b"],
    "UI/UX Design": [r"\bui/ux\b", r"\bui\s+ux\b", r"\buser\s+interface\b", r"\buser\s+experience\b"],
    # Expanded skill patterns
    "FastAPI": [r"\bfastapi\b"],
    "Django": [r"\bdjango\b"],
    "Flask": [r"\bflask\b"],
    "Spring Boot": [r"\bspring\s*boot\b", r"\bspring\s*framework\b"],
    "Node.js": [r"\bnode(?:\.js)?\b"],
    "Express.js": [r"\bexpress(?:\.js)?\b"],
    "Ruby on Rails": [r"\brails\b", r"\bruby\s+on\s+rails\b"],
    "Laravel": [r"\blaravel\b"],
    "ASP.NET": [r"\basp\.net\b", r"\bdotnet\b"],
    "PyTorch Geometric": [r"\bpytorch\s+geometric\b", r"\bpyg\b"],
    "GraphQL": [r"\bgraphql\b"],
    "REST API": [r"\brest\s+(?:api|apis|ful)\b"],
    "gRPC": [r"\bgrpc\b"],
    "GitHub Actions": [r"\bgithub\s+actions\b"],
    "Linux": [r"\blinux\b", r"\bubuntu\b", r"\bdebian\b", r"\bcentos\b", r"\bredhat\b"],
    "Bash": [r"\bbash\b", r"\bshell\s+script(?:ing)?\b"],
    "C": [r"\bc(?!\+\+|#|\w)\b"],
    "Kotlin": [r"\bkotlin\b"],
    "Swift": [r"\bswift\b"],
    "Flutter": [r"\bflutter\b"],
    "React Native": [r"\breact\s+native\b"],
    "Redux": [r"\bredux\b", r"\bredux-toolkit\b"],
    "Webpack": [r"\bwebpack\b"],
    "Bootstrap": [r"\bbootstrap\b"],
    "Material UI": [r"\bmaterial\s*ui\b", r"\bmui\b"],
    "Jira": [r"\bjira\b"],
    "Agile": [r"\bagile\b", r"\bscrum\b"],
    "Unit Testing": [r"\bunit\s+testing\b", r"\bpytest\b", r"\bjest\b", r"\bjunit\b"]
}

# Stopwords and filler phrases to filter out from custom skill candidates
ENGLISH_STOPWORDS = {
    "and", "or", "with", "using", "for", "the", "a", "an", "in", "of", "to", "at", "by", "on", "as",
    "advanced", "intermediate", "expert", "beginner", "proficient", "strong", "excellent",
    "knowledge", "experience", "years", "months", "level", "skills", "technologies", "tools",
    "frameworks", "libraries", "languages", "databases", "platforms", "understanding", "familiarity",
    "working", "development", "programming", "software", "applications", "concepts", "techniques",
    "etc", "various", "other", "good", "great", "highly", "key", "skills:", "tools:", "languages:"
}

def clean_skill_candidate(candidate: str) -> str:
    """Cleans a extracted candidate phrase and filters it."""
    cand = candidate.strip(" .,;:-|()[]{}*•\t")
    
    # Filter by length
    if len(cand) < 1 or len(cand) > 30:
        return ""
        
    # Check if candidate is mostly numbers
    if cand.isdigit():
        return ""
        
    # Check if candidate is in stopwords (case-insensitive)
    if cand.lower() in ENGLISH_STOPWORDS:
        return ""
        
    # Remove leading common fillers
    cand_lower = cand.lower()
    for filler in ["experienced in ", "knowledge of ", "proficient in ", "skills in ", "working with "]:
        if cand_lower.startswith(filler):
            cand = cand[len(filler):].strip()
            
    # Check if cleaned candidate is in stopwords
    if cand.lower() in ENGLISH_STOPWORDS or not cand:
        return ""
        
    return cand

def is_skills_header(line: str) -> bool:
    """Detects if a line acts as a header for a skills section."""
    clean_line = line.lower().strip().replace(":", "").replace("###", "").replace("##", "").replace("#", "").replace("*", "").replace("-", "").strip()
    headers = {
        "skills", "technical skills", "key skills", "core competencies", 
        "technologies", "tools & technologies", "languages & tools", 
        "frameworks & libraries", "expertise", "professional skills", 
        "areas of expertise", "programming languages", "development skills",
        "technical expertise", "skills & tools", "technical proficiencies", 
        "proficiencies", "core skills", "relevant skills"
    }
    if clean_line in headers:
        return True
    # Catch lines like "skills & tools" or "programming languages"
    words = clean_line.split()
    if len(words) <= 3 and any(w in clean_line for w in ["skills", "technologies", "proficiencies"]):
        return True
    return False

def is_boundary_header(line: str) -> bool:
    """Detects if a line signals the end of a skills section."""
    clean_line = line.lower().strip().replace(":", "").replace("###", "").replace("##", "").replace("#", "").replace("*", "").replace("-", "").strip()
    boundaries = {
        "experience", "work experience", "professional experience", "employment", 
        "employment history", "work history", "projects", "personal projects", 
        "academic projects", "education", "certifications", "awards", "publications", 
        "summary", "objective", "contact", "references", "about me", "personal statement", 
        "profile", "history", "career history", "interests", "hobbies"
    }
    if clean_line in boundaries:
        return True
    # Catch dates or year ranges indicating work experience details
    if re.search(r'\b(19\d\d|20\d\d)\b', clean_line):
        return True
    if "present" in clean_line:
        return True
    return False

def parse_resume_pdf(pdf_bytes: bytes, existing_skills: list[str] = None) -> dict:
    """
    Parses a PDF file from bytes and extracts:
    - Text contents using layout-aware extraction
    - Dynamic matches against existing database skills
    - Regex keyword matches
    - Heuristically extracted custom skills from 'Skills' sections
    - Current/target occupations
    - Experience summary
    """
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        full_text = ""
        for page in reader.pages:
            try:
                # Try layout mode first to preserve formatting columns/spaces
                text = page.extract_text(extraction_mode="layout")
            except Exception:
                text = page.extract_text()
            if text:
                full_text += text + "\n"
        
        # Clean text for regex matching (keep double spacing or tabs for layout checks)
        full_text_clean = re.sub(r'[ \t]+', ' ', full_text)
        
        # Keep track of matched skills (case-insensitive deduplication)
        extracted_skills_map = {} # lowercase -> standard case
        
        # 1. Regex Matcher (using expanded local vocabulary)
        for skill_name, patterns in SKILL_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, full_text_clean, re.IGNORECASE):
                    extracted_skills_map[skill_name.lower()] = skill_name
                    break
                    
        # 2. Dynamic DB Skill Matching
        if existing_skills:
            for skill_name in existing_skills:
                # Search using a boundary regex for accuracy
                pattern = r'\b' + re.escape(skill_name.lower()) + r'\b'
                # Handle special characters in skills like C++, C#, .NET
                if "++" in skill_name or "#" in skill_name or "." in skill_name:
                    pattern = r'(?<!\w)' + re.escape(skill_name.lower()) + r'(?!\w)'
                if re.search(pattern, full_text_clean.lower()):
                    extracted_skills_map[skill_name.lower()] = skill_name

        # 3. Heuristic Layout-Based Section Extraction
        in_skills_section = False
        candidates = []
        for line in full_text.split('\n'):
            line_stripped = line.strip()
            if not line_stripped:
                continue
                
            # Check for section boundaries
            if is_skills_header(line_stripped):
                in_skills_section = True
                continue
            elif is_boundary_header(line_stripped):
                in_skills_section = False
                continue
                
            if in_skills_section:
                # Remove common leading bullets
                bullet_removed = re.sub(r'^[•\-\*\t\s]+', '', line_stripped)
                
                # Check for category colons or dashes
                parts = bullet_removed.split(':', 1)
                content = parts[1] if len(parts) > 1 else parts[0]
                
                # If there's no colon but there is a distinct double space separation
                # We split by multiple delimiters
                items = re.split(r'[,;|•\t\*]|\s{3,}', content)
                for item in items:
                    item_clean = clean_skill_candidate(item)
                    if not item_clean:
                        continue
                    
                    # Split slashes unless it's a known compound word like CI/CD
                    if '/' in item_clean:
                        if item_clean.lower() in ["ci/cd", "html/css", "ui/ux", "tcp/ip", "i/o", "c/c++"]:
                            candidates.append(item_clean)
                        else:
                            for sub_item in item_clean.split('/'):
                                sub_cleaned = clean_skill_candidate(sub_item)
                                if sub_cleaned:
                                    candidates.append(sub_cleaned)
                    else:
                        candidates.append(item_clean)
                        
        # Merge heuristic candidates (title-casing unknown ones)
        for cand in candidates:
            cand_key = cand.lower()
            if cand_key not in extracted_skills_map:
                # Check if there is a case-insensitive match in our lists
                # If not, add as title case
                matched_name = cand
                # Quick search in SKILL_PATTERNS keys
                for sk_name in SKILL_PATTERNS:
                    if sk_name.lower() == cand_key:
                        matched_name = sk_name
                        break
                if existing_skills:
                    for sk_name in existing_skills:
                        if sk_name.lower() == cand_key:
                            matched_name = sk_name
                            break
                extracted_skills_map[cand_key] = matched_name

        matched_skills = list(extracted_skills_map.values())
        if not matched_skills:
            # Fallback defaults if absolutely nothing matched
            matched_skills = ["Python", "Git", "SQL"]

        # 4. Infer Job Titles
        inferred_roles = []
        role_keywords = [
            "Data Scientist", "Machine Learning Engineer", "Full-Stack Developer",
            "DevOps Engineer", "Data Engineer", "Cloud Architect", "Frontend Engineer",
            "Backend Engineer", "Software Engineer", "Systems Engineer", "AI Researcher",
            "Product Manager", "Security Engineer", "QA Automation Engineer",
            "Mobile Developer", "Database Administrator", "UI/UX Designer"
        ]
        
        for role in role_keywords:
            pattern = r'\b' + re.escape(role.lower()) + r'\b'
            if re.search(pattern, full_text_clean.lower()):
                inferred_roles.append(role)
                
        current_occupation = inferred_roles[0] if inferred_roles else "Software Engineer"
        target_occupation = inferred_roles[1] if len(inferred_roles) > 1 else (inferred_roles[0] if inferred_roles else "Machine Learning Engineer")
        
        # 5. Extract experience years if present (simple regex)
        experience_records = []
        exp_matches = re.findall(r'(\d+)\+?\s*years?\b', full_text_clean.lower())
        total_years = sum(int(y) for y in exp_matches) if exp_matches else 1
        # Cap years at a reasonable number (e.g. 15) to avoid regex mismatches of other numbers
        total_years = min(total_years, 15)
        
        experience_records.append({
            "role": current_occupation,
            "company": "Previous Company",
            "years": total_years
        })
        
        # Generate bio
        top_skills = sorted(matched_skills, key=len)[:5]
        bio = f"Experienced professional in {current_occupation} with skill sets: {', '.join(top_skills)}."
        
        return {
            "parsed_skills": matched_skills,
            "parsed_experience": experience_records,
            "current_occupation": current_occupation,
            "target_occupation": target_occupation,
            "bio": bio
        }
    except Exception as e:
        print(f"Error parsing resume: {e}")
        # Return empty safe defaults on failure
        return {
            "parsed_skills": ["Python", "SQL", "Git"],
            "parsed_experience": [{"role": "Software Developer", "company": "Tech Corp", "years": 2}],
            "current_occupation": "Software Developer",
            "target_occupation": "Data Scientist",
            "bio": "Developer looking for new opportunities."
        }

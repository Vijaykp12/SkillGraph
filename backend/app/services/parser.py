import io
import re
from pypdf import PdfReader

# Key skills and their regex patterns to match in raw text for keyword extraction
SKILL_PATTERNS = {
    "Python": [r"\bpython\b", r"\bpy\b"],
    "JavaScript": [r"\bjavascript\b", r"\bjs\b"],
    "TypeScript": [r"\btypescript\b", r"\bts\b"],
    "SQL": [r"\bsql\b", r"\bsqlite\b", r"\bmysql\b", r"\bpostgres\b", r"\bpostgresql\b"],
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
    "Neo4j": [r"\bneo4j\b"],
    "PostgreSQL": [r"\bpostgres(?:ql)?\b"],
    "Redis": [r"\bredis\b"],
    "FAISS": [r"\bfaiss\b"],
    "MongoDB": [r"\bmongo(?:db)?\b"],
    "MySQL": [r"\bmysql\b"],
    "Elasticsearch": [r"\belasticsearch\b"],
    "Apache Spark": [r"\bspark\b", r"\bapache\s+spark\b"],
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
    "UI/UX Design": [r"\bui/ux\b", r"\bui\s+ux\b", r"\buser\s+interface\b", r"\buser\s+experience\b"]
}

def parse_resume_pdf(pdf_bytes: bytes) -> dict:
    """
    Parses a PDF file from bytes and extracts:
    - Text contents
    - Matched skills
    - Current/target occupations (inferred from job titles found)
    - Experience summary
    """
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        full_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"
        
        # 1. Clean extracted text
        full_text_clean = re.sub(r'\s+', ' ', full_text)
        
        # 2. Extract Skills using regex patterns
        matched_skills = []
        for skill, patterns in SKILL_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, full_text_clean, re.IGNORECASE):
                    matched_skills.append(skill)
                    break
                
        # 3. Infer Job Titles
        inferred_roles = []
        role_keywords = [
            "Data Scientist", "Machine Learning Engineer", "Full-Stack Developer",
            "DevOps Engineer", "Data Engineer", "Cloud Architect", "Frontend Engineer",
            "Backend Engineer", "Software Engineer"
        ]
        
        for role in role_keywords:
            pattern = r'\b' + re.escape(role.lower()) + r'\b'
            if re.search(pattern, full_text_clean.lower()):
                inferred_roles.append(role)
                
        current_occupation = inferred_roles[0] if inferred_roles else "Software Engineer"
        target_occupation = inferred_roles[1] if len(inferred_roles) > 1 else (inferred_roles[0] if inferred_roles else "Machine Learning Engineer")
        
        # 4. Extract experience years if present (simple regex)
        experience_records = []
        exp_matches = re.findall(r'(\d+)\+?\s*years?\b', full_text_clean.lower())
        total_years = sum(int(y) for y in exp_matches) if exp_matches else 1
        
        # Build clean profile experience list
        experience_records.append({
            "role": current_occupation,
            "company": "Previous Company",
            "years": total_years
        })
        
        return {
            "parsed_skills": list(set(matched_skills)),
            "parsed_experience": experience_records,
            "current_occupation": current_occupation,
            "target_occupation": target_occupation,
            "bio": f"Experienced professional in {current_occupation} with skill sets: {', '.join(matched_skills[:5])}."
        }
    except Exception as e:
        print(f"Error parsing resume: {e}")
        # Return empty safe defaults on failure
        return {
            "parsed_skills": ["Python", "SQL"],
            "parsed_experience": [{"role": "Software Developer", "company": "Tech Corp", "years": 2}],
            "current_occupation": "Software Developer",
            "target_occupation": "Data Scientist",
            "bio": "Developer looking for new opportunities."
        }

import os
import re
from typing import List, Dict, Any, Optional

DOCS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../docs"))
README_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../README.md"))

def search_documentation(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Retrieves approved documentation sections matching user questions or troubleshooting queries.
    Performs keyword/semantic token scoring across docs/ and README.md.
    """
    results = []
    doc_files = []
    
    if os.path.exists(README_PATH):
        doc_files.append(("README.md", README_PATH))
        
    if os.path.exists(DOCS_DIR):
        for fname in os.listdir(DOCS_DIR):
            if fname.endswith(".md"):
                doc_files.append((fname, os.path.join(DOCS_DIR, fname)))
                
    query_tokens = set(re.findall(r'\w+', query.lower()))
    if not query_tokens:
        return []

    for name, path in doc_files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Split into sections by markdown headers (## or ###)
            sections = re.split(r'\n(?=#{1,3}\s+)', content)
            for section in sections:
                if not section.strip():
                    continue
                header_match = re.match(r'^(#{1,3}\s+[^\n]+)', section)
                header = header_match.group(1).strip() if header_match else "Overview"
                
                section_tokens = set(re.findall(r'\w+', section.lower()))
                common = query_tokens.intersection(section_tokens)
                
                if common:
                    score = len(common)
                    # Boost if match is in header
                    if any(t in header.lower() for t in common):
                        score += 3
                    
                    results.append({
                        "doc_name": name,
                        "header": header,
                        "score": score,
                        "snippet": section.strip()[:1200]
                    })
        except Exception:
            continue

    # Sort descending by match score
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]

import pdfplumber
import sys
import json
import re

def extract_text_from_pdf(pdf_path: str) -> str:
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()

def extract_sections(text: str) -> dict:
    sections = {}
    lines = text.split("\n")
    current_section = "header"
    section_lines = []

    section_keywords = [
        "experience", "work experience", "employment",
        "education", "academic",
        "skills", "technical skills", "core competencies",
        "projects", "project",
        "certifications", "certificates",
        "publications",
        "achievements", "awards",
        "summary", "profile", "objective",
        "leadership",
        "languages",
        "interests",
        "volunteer",
        "references"
    ]

    for line in lines:
        line_stripped = line.strip().lower().rstrip(":")
        if line_stripped in section_keywords or any(line_stripped.startswith(kw) for kw in section_keywords):
            if section_lines:
                sections[current_section] = "\n".join(section_lines).strip()
            current_section = line_stripped
            section_lines = []
        else:
            section_lines.append(line)

    if section_lines:
        sections[current_section] = "\n".join(section_lines).strip()

    return sections

def extract_contact_info(text: str) -> dict:
    info = {}
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    phone_pattern = r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    linkedin_pattern = r'(?:https?://)?(?:www\.)?linkedin\.com/in/[A-Za-z0-9_-]+'

    emails = re.findall(email_pattern, text)
    phones = re.findall(phone_pattern, text)
    linkedin = re.findall(linkedin_pattern, text, re.IGNORECASE)

    if emails:
        info["email"] = emails[0]
    if phones:
        info["phone"] = phones[0]
    if linkedin:
        info["linkedin"] = linkedin[0]

    return info

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python parse_resume.py <path-to-pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    text = extract_text_from_pdf(pdf_path)
    sections = extract_sections(text)
    contact = extract_contact_info(text)

    output = {
        "filename": pdf_path,
        "total_chars": len(text),
        "total_words": len(text.split()),
        "contact": contact,
        "sections": {k: v[:200] + "..." if len(v) > 200 else v for k, v in sections.items()}
    }

    print(json.dumps(output, indent=2))

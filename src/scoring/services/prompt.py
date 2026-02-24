from scoring.models import ATSCandidate, AtsDocuments, ATSVacancy

SYSTEM_PROMPT = """\
You are an expert recruitment analyst. Your task is to evaluate how well a candidate
fits a specific vacancy. Analyze all provided candidate information against the vacancy
requirements and produce a numerical score with clear reasoning.

## Scoring Criteria
Evaluate the candidate across these dimensions:
1. **Skills match** — Does the candidate have the required skills, certifications,
and qualifications?
2. **Experience relevance** — Is the candidate's work history relevant to the role?
3. **Availability & schedule** — Can the candidate work the required hours and days?
4. **Location & commute** — Is the candidate within reasonable distance or willing to commute?
5. **Salary expectations** — Do the candidate's salary expectations align with the role?
6. **Motivation** — Does the candidate show genuine interest in this type of work?
7. **Language requirements** — Can the candidate communicate in the required language(s)?

## Scoring Rubric
- **90-100**: Excellent fit — meets or exceeds all requirements
- **70-89**: Good fit — meets most requirements with minor gaps
- **50-69**: Moderate fit — meets some requirements but has notable gaps
- **30-49**: Weak fit — significant mismatches in key areas
- **0-29**: Poor fit — fundamental mismatches, unlikely to succeed in this role

## Important Notes
- Candidate information may be in Dutch — your reasoning MUST be in English.
- Base your score strictly on the evidence provided. Do not assume information not present.
- Provide 2-4 sentences of reasoning explaining the score."""


def build_user_prompt(
    candidate: ATSCandidate,
    vacancy: ATSVacancy,
    ats_documents: AtsDocuments,
) -> str:
    parts = []

    # --- Candidate section ---
    parts.append("## Candidate Information")
    name = candidate.name or f"{candidate.firstname} {candidate.lastname}".strip()
    if name:
        parts.append(f"**Name**: {name}")
    if candidate.email:
        parts.append(f"**Email**: {candidate.email}")
    if candidate.phone:
        parts.append(f"**Phone**: {candidate.phone}")
    if candidate.address:
        parts.append(f"**Address**: {candidate.address}")
    if candidate.job and (candidate.job.title or candidate.job.company):
        role_parts = []
        if candidate.job.title:
            role_parts.append(candidate.job.title)
        if candidate.job.company:
            role_parts.append(f"at {candidate.job.company}")
        parts.append(f"**Current role**: {' '.join(role_parts)}")

    # --- Documents section ---
    if ats_documents.resume:
        parts.append("\n### Resume")
        parts.append(ats_documents.resume)
    if ats_documents.job_description:
        parts.append("\n### Job Description")
        parts.append(ats_documents.job_description)
    if ats_documents.assessment:
        parts.append("\n### Assessment")
        parts.append(ats_documents.assessment)

    # --- Vacancy section ---
    parts.append("\n## Vacancy Description")
    if vacancy.title:
        parts.append(f"**Title**: {vacancy.title}")
    if vacancy.description:
        parts.append(vacancy.description)
    if vacancy.hard_requirements:
        parts.append(f"\n**Hard Requirements**: {vacancy.hard_requirements}")
    if vacancy.soft_requirements:
        parts.append(f"\n**Soft Requirements**: {vacancy.soft_requirements}")
    if vacancy.about_company:
        parts.append(f"\n**About the Company**: {vacancy.about_company}")
    addr = vacancy.address
    if addr and (addr.city or addr.country):
        location_parts = [p for p in [addr.street, addr.city, addr.zip_code, addr.country] if p]
        parts.append(f"\n**Location**: {', '.join(location_parts)}")

    return "\n".join(parts)

import os
import json
import sys
import re
import requests
from github import Github, Auth

# -----------------------------
# Environment Variables
# -----------------------------
repo_name = os.getenv("GITHUB_REPOSITORY")
token = os.getenv("GITHUB_TOKEN")
gemini_api_key = os.getenv("GEMINI_API_KEY")

if not gemini_api_key or not repo_name or not token:
    sys.exit("Missing required environment variables")

# -----------------------------
# Read PR event
# -----------------------------
with open(os.getenv("GITHUB_EVENT_PATH")) as f:
    event = json.load(f)

pr_number = event["number"]

# -----------------------------
# GitHub setup
# -----------------------------
g = Github(auth=Auth.Token(token))
repo = g.get_repo(repo_name)
pr = repo.get_pull(int(pr_number))

# -----------------------------
# Gather changed files and diff
# -----------------------------
changed_files = []
diff_context = []

for f in pr.get_files():
    changed_files.append({"filename": f.filename, "patch": f.patch})
    if f.patch:
        diff_context.append({"filename": f.filename, "changed_lines": f.patch})

# -----------------------------
# Comprehensive Checklist Prompt
# -----------------------------
checklist_prompt = """
Review the PR changes and provide a detailed AI review.

Rules:
- Use ✅ for pass and ❌ for fail.
- Keep comments short (1 line max).
- Group items by category as headers.
- Detect general syntax errors in the code.
- Detect TypeScript syntax errors specifically.
- Check for missing semicolons where applicable.
- Flag new or insecure dependencies.
- Suggest performance/efficiency improvements.
- Focus on changed lines only and provide inline suggestions in this format:

INLINE SUGGESTION:
file: <filename>
line: <line_number>
comment: <your suggestion>

CATEGORIES:

1️⃣ Readability & Maintainability
- Code follows project coding standards / naming conventions
- Test case names are descriptive, meaningful, and consistent
- Proper indentation, spacing, and formatting
- Functions are modular (single responsibility)
- Comments added only where needed

2️⃣ Test Case Design
- Scripts reflect business requirements
- No duplication, reusable components used
- Test data parameterized (not hardcoded)
- Assertions are meaningful and specific
- Edge cases and negative tests included

3️⃣ Framework & Best Practices
- Follows framework structure (e.g., POM, BDD)
- Reusable utilities/helpers used
- Adheres to DRY and SOLID principles
- Proper waits (explicit > implicit > no sleep)
- No hardcoded locators, URLs, or credentials

4️⃣ Code Quality
- Proper exception handling
- Standardized logging, minimal prints
- No unused imports/variables/commented code
- Dependencies justified

5️⃣ Scalability & Maintainability
- Locators are robust & maintainable
- Test data externalized (CSV/JSON/Config)
- Environment configurable (not hardcoded)
- Code changes don’t break existing suites

6️⃣ Execution & Reporting
- Scripts run independently (no dependency)
- Supports parallel execution
- Reports/logs are consistent and meaningful
- Failures provide useful debug info

7️⃣ Version Control & Collaboration
- Commit messages are clear & follow guidelines
- No sensitive info in repo
- Changes scoped properly
- PR description includes summary & test evidence

At the end, provide an overall recommendation in this exact format:

Overall Recommendation: Good to merge ✅
or
Overall Recommendation: Needs changes ❌
"""

# -----------------------------
# Compose prompt for AI
# -----------------------------
prompt = f"""
PR Title: {pr.title}
PR Description: {pr.body}
Changed Files: {changed_files}
Diff Context: {diff_context}

{checklist_prompt}
"""

# -----------------------------
# Call Gemini API
# -----------------------------
url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
headers = {"Content-Type": "application/json", "X-goog-api-key": gemini_api_key}
payload = {"contents": [{"parts": [{"text": prompt}]}]}

response = requests.post(url, headers=headers, json=payload)

if response.status_code != 200:
    sys.exit(f"Gemini API call failed with status code {response.status_code}")

result = response.json()
if "candidates" not in result:
    sys.exit("No candidates returned from Gemini API")

ai_review = result["candidates"][0]["content"]["parts"][0]["text"]

# -----------------------------
# Format AI review: color + collapsible ✅ / bold ❌
# -----------------------------
def format_ai_review_colored(ai_text):
    formatted_lines = []
    for line in ai_text.splitlines():
        line = line.strip()
        if line.startswith("✅"):
            # Green + collapsible
            formatted_lines.append(
                f'<details><summary><span style="color:green;">{line}</span></summary></details>'
            )
        elif line.startswith("❌"):
            # Red + bold
            formatted_lines.append(f'<b><span style="color:red;">{line}</span></b>')
        else:
            # Keep other lines (category headers, overall recommendation)
            formatted_lines.append(line)
    return "\n".join(formatted_lines)

ai_review_formatted = format_ai_review_colored(ai_review)

# -----------------------------
# Post formatted AI review as a PR comment
# -----------------------------
pr.create_issue_comment(f"### 🤖 AI Code Review\n\n{ai_review_formatted}")

# -----------------------------
# Parse inline suggestions from AI text
# -----------------------------
inline_comments = []
pattern = r"INLINE SUGGESTION:\s*file:\s*(.*)\s*line:\s*(\d+)\s*comment:\s*(.*)"
matches = re.findall(pattern, ai_review, re.MULTILINE)

for match in matches:
    filename, line_number, comment = match
    inline_comments.append({
        "path": filename.strip(),
        "line": int(line_number.strip()),
        "body": comment.strip()
    })

# -----------------------------
# Post inline comments as review
# -----------------------------
if inline_comments:
    pr.create_review(event="COMMENT", comments=inline_comments)

# -----------------------------
# Auto-merge if AI approves
# -----------------------------
if "Overall Recommendation: Good to merge ✅" in ai_review:
    try:
        pr.merge(commit_title=f"Auto-merged PR #{pr_number}: {pr.title}", merge_method="squash")
    except Exception:
        pass

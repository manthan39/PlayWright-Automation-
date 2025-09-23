import os
import json
import sys
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
- Detect syntax errors, runtime issues, and failing tests.
- Include filename and line number for each issue in this format:

FILE: <filename>
LINE: <line_number>
ISSUE: <short description of problem/failure>

Focus on changed lines only.

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
# Format AI review: color + collapsible ✅ / bold ❌ with file & line
# -----------------------------
def format_ai_review_with_file_lines(ai_text):
    formatted_lines = []
    current_file = ""
    current_line = ""
    for line in ai_text.splitlines():
        line = line.strip()
        if line.startswith("FILE:"):
            current_file = line.replace("FILE:", "").strip()
            formatted_lines.append(f"\n### File: {current_file}")
        elif line.startswith("LINE:"):
            current_line = line.replace("LINE:", "").strip()
            formatted_lines.append(f"- Line: {current_line}")
        elif line.startswith("ISSUE:"):
            issue_text = line.replace("ISSUE:", "").strip()
            if "✅" in issue_text:
                formatted_lines.append(
                    f"<details><summary><span style='color:green;'>{issue_text}</span></summary></details>"
                )
            elif "❌" in issue_text:
                formatted_lines.append(
                    f"<b><span style='color:red;'>{issue_text}</span></b>"
                )
            else:
                formatted_lines.append(issue_text)
        else:
            formatted_lines.append(line)
    return "\n".join(formatted_lines)

ai_review_formatted = format_ai_review_with_file_lines(ai_review)

# -----------------------------
# Post AI review as a single PR comment
# -----------------------------
pr.create_issue_comment(f"### 🤖 AI Code Review\n\n{ai_review_formatted}")

# -----------------------------
# Auto-merge if AI approves
# -----------------------------
if "Overall Recommendation: Good to merge ✅" in ai_review:
    try:
        pr.merge(commit_title=f"Auto-merged PR #{pr_number}: {pr.title}", merge_method="squash")
    except Exception:
        pass

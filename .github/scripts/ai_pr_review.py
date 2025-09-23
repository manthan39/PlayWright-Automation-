import os
import json
import sys
import requests
from github import Github, Auth

repo_name = os.getenv("GITHUB_REPOSITORY")
token = os.getenv("GITHUB_TOKEN")
gemini_api_key = os.getenv("GEMINI_API_KEY")

if not gemini_api_key:
    sys.exit(1)

with open(os.getenv("GITHUB_EVENT_PATH")) as f:
    event = json.load(f)
pr_number = event["number"]

g = Github(auth=Auth.Token(token))
repo = g.get_repo(repo_name)
pr = repo.get_pull(int(pr_number))

changed_files = []
diff_context = []

for f in pr.get_files():
    changed_files.append({"filename": f.filename, "patch": f.patch})
    if f.patch:
        diff_context.append({"filename": f.filename, "changed_lines": f.patch})

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

- Include a checklist with the following format.
- For items that pass, show green text: <span style="color:green">Yes ✅</span>
- For items that fail, show red text: <span style="color:red">No ❌</span>
- Fill in each item appropriately based on your review.

Readability & Maintainability:
- Code follows project coding standards / naming conventions: <span style="color:green">Yes ✅</span> / <span style="color:red">No ❌</span>
- Test case names are descriptive, meaningful, and consistent: <span style="color:green">Yes ✅</span> / <span style="color:red">No ❌</span>
- Proper indentation, spacing, and formatting: <span style="color:green">Yes ✅</span> / <span style="color:red">No ❌</span>
- Functions are modular (single responsibility): <span style="color:green">Yes ✅</span> / <span style="color:red">No ❌</span>
- Comments added only where needed: <span style="color:green">Yes ✅</span> / <span style="color:red">No ❌</span>

Test Case Design:
- Scripts reflect business requirements: <span style="color:green">Yes ✅</span> / <span style="color:red">No ❌</span>
- No duplication, reusable components used: <span style="color:green">Yes ✅</span> / <span style="color:red">No ❌</span>
- Test data parameterized (not hardcoded): <span style="color:green">Yes ✅</span> / <span style="color:red">No ❌</span>
- Assertions are meaningful and specific: <span style="color:green">Yes ✅</span> / <span style="color:red">No ❌</span>
- Edge cases and negative tests included: <span style="color:green">Yes ✅</span> / <span style="color:red">No ❌</span>

Framework & Best Practices:
- Follows framework structure (e.g., POM, BDD): <span style="color:green">Yes ✅</span> / <span style="color:red">No ❌</span>
- Reusable utilities/helpers used: <span style="color:green">Yes ✅</span> / <span style="color:red">No ❌</span>
- Adheres to DRY and SOLID principles: <span style="color:green">Yes ✅</span> / <span style="color:red">No ❌</span>
- Proper waits (explicit > implicit > no sleep): <span style="color:green">Yes ✅</span> / <span style="color:red">No ❌</span>
- No hardcoded locators, URLs, or credentials: <span style="color:green">Yes ✅</span> / <span style="color:red">No ❌</span>

Code Quality:
- Proper exception handling: <span style="color:green">Yes ✅</span> / <span style="color:red">No ❌</span>
- Standardized logging, minimal prints: <span style="color:green">Yes ✅</span> / <span style="color:red">No ❌</span>
- No unused imports/variables/commented code: <span style="color:green">Yes ✅</span> / <span style="color:red">No ❌</span>
- Dependencies justified: <span style="color:green">Yes ✅</span> / <span style="color:red">No ❌</span>

Scalability & Maintainability:
- Locators are robust & maintainable: <span style="color:green">Yes ✅</span> / <span style="color:red">No ❌</span>
- Test data externalized (CSV/JSON/Config): <span style="color:green">Yes ✅</span> / <span style="color:red">No ❌</span>
- Environment configurable (not hardcoded): <span style="color:green">Yes ✅</span> / <span style="color:red">No ❌</span>
- Code changes don’t break existing suites: <span style="color:green">Yes ✅</span> / <span style="color:red">No ❌</span>

Execution & Reporting:
- Scripts run independently (no dependency): <span style="color:green">Yes ✅</span> / <span style="color:red">No ❌</span>
- Supports parallel execution: <span style="color:green">Yes ✅</span> / <span style="color:red">No ❌</span>
- Reports/logs are consistent and meaningful: <span style="color:green">Yes ✅</span> / <span style="color:red">No ❌</span>
- Failures provide useful debug info: <span style="color:green">Yes ✅</span> / <span style="color:red">No ❌</span>

Version Control & Collaboration:
- Commit messages are clear & follow guidelines: <span style="color:green">Yes ✅</span> / <span style="color:red">No ❌</span>
- No sensitive info in repo: <span style="color:green">Yes ✅</span> / <span style="color:red">No ❌</span>
- Changes scoped properly: <span style="color:green">Yes ✅</span> / <span style="color:red">No ❌</span>
- PR description includes summary & test evidence: <span style="color:green">Yes ✅</span> / <span style="color:red">No ❌</span>

- At the end, provide an overall recommendation in this exact format:

Overall Recommendation: Good to merge ✅
or
Overall Recommendation: Needs changes ❌
"""

url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
headers = {"Content-Type": "application/json", "X-goog-api-key": gemini_api_key}
payload = {"contents": [{"parts": [{"text": prompt}]}]}

response = requests.post(url, headers=headers, json=payload)

if response.status_code != 200:
    sys.exit(1)

result = response.json()

if "candidates" not in result:
    sys.exit(1)

ai_review = result["candidates"][0]["content"]["parts"][0]["text"]

pr.create_issue_comment(f"### 🤖 AI Code Review\n\n{ai_review}")

# -----------------------------
# Parse inline suggestions from AI text
# -----------------------------
import re

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
# Post inline comments as a review
# -----------------------------
if inline_comments:
    pr.create_review(event="COMMENT", comments=inline_comments)

# -----------------------------
# Auto-merge if AI approves
# -----------------------------
if "Overall Recommendation: Good to merge ✅" in ai_review:
    try:
        pr.merge(commit_title=f"Auto-merged PR #{pr_number}: {pr.title}", merge_method="squash")
    except:
        pass

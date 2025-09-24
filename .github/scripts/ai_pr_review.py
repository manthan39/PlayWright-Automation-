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

Additional Mandatory Rules:
- Each test case in `.spec.ts` must include an author block in this format:
/**
 * @author John Doe
 * @createdDate YYYY-MM-DD
 * @updatedDate YYYY-MM-DD
 */
- Highlight if any execution step could exceed 20 seconds, including filename and line number.
- Highlight any syntax error with filename and line number.

By following these standards, we ensure:
* Readability: Code is easy to understand by anyone on the team.
* Maintainability: Tests are easy to update, debug, and extend.
* Consistency: A uniform approach across all projects and teams.
* Collaboration: Smoother knowledge transfer and peer reviews.
* Efficiency: Faster development and execution of automated tests.
Adherence to these standards is a mandatory part of our quality engineering process.

CATEGORIES:

1️⃣ General Principles
- Clean, concise, self-explanatory code
- DRY (Don’t Repeat Yourself)
- KISS (Keep It Simple, Stupid)
- Single Responsibility Principle
- Fail fast: immediate feedback on errors

2️⃣ Naming Conventions
- Projects/Modules: PascalCase
- Test files/classes: PascalCase (e.g., LoginPageTests)
- Test methods: test_ / verify_ prefix, descriptive names
- Variables: camelCase
- Constants: ALL_CAPS
- Page object locators: prefixed descriptive names

3️⃣ Code Formatting & Structure
- Consistent indentation (no mixing spaces/tabs)
- Line length < 120 chars
- Organized imports (standard → third-party → project)
- No unused/commented code

4️⃣ Comments & Documentation
- Author block in each `.spec.ts` test
- Explain “why”, not “what”
- Concise, up-to-date comments
- Use TODO for improvements
- Use language-appropriate docstrings

5️⃣ Test Design & Structure
- POM / SOM applied properly
- Test data externalized (CSV/JSON/Config)
- Tests atomic and independent
- AAA pattern (Arrange, Act, Assert)
- Assertions meaningful, with messages
- Screenshots/logging on failure
- Logging with appropriate levels

6️⃣ Error Handling & Robustness
- Proper exception handling (no blanket catch)
- Explicit waits > Thread.sleep
- Idempotent tests (repeatable runs)
- Retries documented only when justified

7️⃣ Framework & Best Practices
- Reusable helpers/utilities
- Robust maintainable locators
- No hardcoded credentials, URLs, or locators
- DRY and SOLID principles
- Parallel execution supported

8️⃣ Execution & Reporting
- Tests run independently
- Reporting/logging meaningful
- Failures provide debug info

9️⃣ Version Control & Collaboration
- Commit messages are clear & follow guidelines
- No sensitive info in repo
- Changes scoped properly
- PR description includes summary & test evidence
- ❌ Highlight if PR Title or Description is missing, vague, or unhelpful

10️⃣ Framework Specific Guidelines (Playwright)
- Prefer stable locators (ID > Name > CSS > XPath)
- Handle dynamic elements robustly
- Custom utilities documented

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
# Format AI review with file + line highlighting
# -----------------------------
def format_ai_review_with_file_lines(ai_text):
    formatted_lines = []
    current_file = ""
    current_line = ""
    for line in ai_text.splitlines():
        line = line.strip()
        if line.startswith("FILE:"):
            current_file = line.replace("FILE:", "").strip()
            formatted_lines.append(f"\n### 📄 File: `{current_file}`")
        elif line.startswith("LINE:"):
            current_line = line.replace("LINE:", "").strip()
            formatted_lines.append(f"- Line: {current_line}")
        elif line.startswith("ISSUE:"):
            issue_text = line.replace("ISSUE:", "").strip()
            if "✅" in issue_text:
                formatted_lines.append(
                    f"<details><summary><span style='color:green;'>{issue_text}</span></summary></details>"
                )
            elif "❌" in issue_text or "syntax error" in issue_text.lower() or "20 sec" in issue_text.lower() or "author" in issue_text.lower():
                formatted_lines.append(
                    f"<b><span style='color:red;'>❌ {issue_text}</span></b>"
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

import os
import requests
from github import Github

# GitHub context
repo_name = os.getenv("GITHUB_REPOSITORY")
pr_number = os.getenv("GITHUB_REF").split("/")[-2]  # Extract PR number
token = os.getenv("GITHUB_TOKEN")
gemini_api_key = os.getenv("GEMINI_API_KEY")

g = Github(token)
repo = g.get_repo(repo_name)
pr = repo.get_pull(int(pr_number))

# Get changed files
changed_files = []
for f in pr.get_files():
    changed_files.append({
        "filename": f.filename,
        "patch": f.patch
    })

# PR checklist prompt (instructing Gemini on response style)
checklist_prompt = """
You are a strict PR reviewer. Review the PR changes against this checklist:

Categories:
1. Readability & Maintainability
2. Test Case Design
3. Framework & Best Practices
4. Code Quality
5. Scalability & Maintainability
6. Execution & Reporting
7. Version Control & Collaboration

Checklist Items:
- Code follows project coding standards / naming conventions
- Test case names are descriptive, meaningful, and consistent
- Proper indentation, spacing, and formatting
- Functions are modular (single responsibility)
- Comments added only where needed
- Scripts reflect business requirements
- No duplication, reusable components used
- Test data parameterized (not hardcoded)
- Assertions are meaningful and specific
- Edge cases and negative tests included
- Follows framework structure (POM, BDD, etc.)
- Reusable utilities/helpers used
- Adheres to DRY and SOLID principles
- Proper waits (explicit > implicit > no sleep)
- No hardcoded locators, URLs, or credentials
- Proper exception handling
- Standardized logging, minimal prints
- No unused imports/variables/commented code
- Dependencies justified
- Locators are robust & maintainable
- Test data externalized (CSV/JSON/Config)
- Environment configurable (not hardcoded)
- Code changes don’t break existing suites
- Scripts run independently (no dependency)
- Supports parallel execution
- Reports/logs are consistent and meaningful
- Failures provide useful debug info
- Commit messages are clear & follow guidelines
- No sensitive info in repo
- Changes scoped properly
- PR description includes summary & test evidence

STRICT RESPONSE FORMAT:
- Always use ✅ for pass, ❌ for fail
- Group items under their category with markdown headers (###)
- Keep comments short (1 line max)
- If pass → no comment needed
- If fail → add short fix suggestion after an arrow (→)
- Do not output anything except this structured review

Example:

### 📝 Readability & Maintainability
- ✅ Code follows project standards
- ❌ Proper indentation → Fix spacing in utils.py
- ✅ Functions are modular
"""

# Call Gemini API
url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
headers = {"Content-Type": "application/json"}
params = {"key": gemini_api_key}

prompt = f"""
PR Title: {pr.title}
PR Description: {pr.body}
Changed Files: {changed_files}

{checklist_prompt}
"""

payload = {
    "contents": [
        {"parts": [{"text": prompt}]}
    ]
}

response = requests.post(url, headers=headers, params=params, json=payload)
result = response.json()

# Extract AI output
ai_review = result["candidates"][0]["content"]["parts"][0]["text"]

# Post review as comment on PR
pr.create_issue_comment(f"### 🤖 AI Code Review\n\n{ai_review}")

import os
import json
import sys
import requests
from github import Github, Auth

# -----------------------------
# GitHub & environment setup
# -----------------------------
repo_name = os.getenv("GITHUB_REPOSITORY")
token = os.getenv("GITHUB_TOKEN")
gemini_api_key = os.getenv("GEMINI_API_KEY")

if not gemini_api_key:
    print("❌ ERROR: GEMINI_API_KEY is missing. Set it in GitHub Secrets.")
    sys.exit(1)

# Load PR number safely from GitHub event payload
with open(os.getenv("GITHUB_EVENT_PATH")) as f:
    event = json.load(f)
pr_number = event["number"]

# Connect to GitHub
g = Github(auth=Auth.Token(token))
repo = g.get_repo(repo_name)
pr = repo.get_pull(int(pr_number))

# Collect changed files
changed_files = [{"filename": f.filename, "patch": f.patch} for f in pr.get_files()]

# -----------------------------
# Build the enhanced checklist prompt
# -----------------------------
checklist_prompt = """
Review the PR changes and provide a detailed AI review.

Rules:
- Use ✅ for pass and ❌ for fail.
- Keep comments short (1 line max).
- Group items by category as headers.
- Detect syntax errors in the code.
- Check for missing semicolons (for JS, Java, or similar languages).
- At the end, provide an overall recommendation: "Good to merge ✅" or "Needs changes ❌".

### 📝 Readability & Maintainability
- Code follows project coding standards / naming conventions
- Test case names are descriptive & consistent
- Proper indentation & formatting
- Functions are modular
- Comments added only where needed

### 🧪 Test Case Design
- Scripts reflect business requirements
- No duplication / reusable components used
- Test data parameterized
- Assertions are meaningful
- Edge cases included

### ⚙️ Framework & Best Practices
- Follows framework structure (POM, BDD)
- Reusable helpers used
- Adheres to DRY and SOLID
- Proper waits
- No hardcoded locators/credentials

### 🧹 Code Quality
- Proper exception handling
- Standardized logging
- No unused imports/variables/commented code
- Dependencies justified

### 📈 Scalability & Maintainability
- Robust & maintainable locators
- Test data externalized
- Environment configurable
- No breaking changes

### 🚀 Execution & Reporting
- Scripts run independently
- Supports parallel execution
- Reports/logs meaningful
- Failures provide debug info

### 🔄 Version Control & Collaboration
- Commit messages are clear
- No sensitive info in repo
- Changes scoped properly
- PR description includes summary & test evidence

Extra checks:
- Check for syntax errors
- Check for missing semicolons where applicable
- Provide an overall recommendation: Good to merge ✅ or Needs changes ❌
"""

prompt = f"""
PR Title: {pr.title}
PR Description: {pr.body}
Changed Files: {changed_files}

{checklist_prompt}
"""

# -----------------------------
# Gemini API call (official format)
# -----------------------------
url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
headers = {
    "Content-Type": "application/json",
    "X-goog-api-key": gemini_api_key
}
payload = {
    "contents": [
        {
            "parts": [
                {"text": prompt}
            ]
        }
    ]
}

response = requests.post(url, headers=headers, json=payload)

if response.status_code != 200:
    print("❌ Gemini API request failed")
    print("Status:", response.status_code)
    print("Response:", response.text)
    sys.exit(1)

result = response.json()

if "candidates" not in result:
    print("❌ Gemini API did not return candidates")
    print(json.dumps(result, indent=2))
    sys.exit(1)

# Extract AI review
ai_review = result["candidates"][0]["content"]["parts"][0]["text"]

# -----------------------------
# Post review as a PR comment
# -----------------------------
pr.create_issue_comment(f"### 🤖 AI Code Review\n\n{ai_review}")
print("✅ AI Review posted to PR")

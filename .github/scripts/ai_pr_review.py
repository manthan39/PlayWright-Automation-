import os
import requests
from github import Github, Auth
import json
import sys

# GitHub context
repo_name = os.getenv("GITHUB_REPOSITORY")
token = os.getenv("GITHUB_TOKEN")
gemini_api_key = os.getenv("GEMINI_API_KEY")

if not gemini_api_key:
    print("❌ ERROR: GEMINI_API_KEY is missing. Did you set it in GitHub Secrets?")
    sys.exit(1)

# Load PR number safely
with open(os.getenv("GITHUB_EVENT_PATH")) as f:
    event = json.load(f)
pr_number = event["number"]

g = Github(auth=Auth.Token(token))
repo = g.get_repo(repo_name)
pr = repo.get_pull(int(pr_number))

# Collect changed files
changed_files = [{"filename": f.filename, "patch": f.patch} for f in pr.get_files()]

prompt = f"""
PR Title: {pr.title}
PR Description: {pr.body}
Changed Files: {changed_files}

(… your structured checklist prompt …)
"""

# Call Gemini API
url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
headers = {"Content-Type": "application/json"}
params = {"key": gemini_api_key}
payload = {"contents": [{"parts": [{"text": prompt}]}]}

response = requests.post(url, headers=headers, params=params, json=payload)

# Check API response
if response.status_code != 200:
    print("❌ Gemini API request failed")
    print("Status:", response.status_code)
    print("Response:", response.text)
    sys.exit(1)

result = response.json()

if "candidates" not in result:
    print("❌ Gemini API did not return candidates")
    print("Full Response:", json.dumps(result, indent=2))
    sys.exit(1)

# Extract AI review
ai_review = result["candidates"][0]["content"]["parts"][0]["text"]

# Post to PR
pr.create_issue_comment(f"### 🤖 AI Code Review\n\n{ai_review}")
print("✅ AI Review posted to PR")

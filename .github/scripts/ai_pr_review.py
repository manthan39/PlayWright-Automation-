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
    print("❌ ERROR: GEMINI_API_KEY is missing. Set it in GitHub Secrets.")
    sys.exit(1)

# Load PR number from event
with open(os.getenv("GITHUB_EVENT_PATH")) as f:
    event = json.load(f)
pr_number = event["number"]

g = Github(auth=Auth.Token(token))
repo = g.get_repo(repo_name)
pr = repo.get_pull(int(pr_number))

# Collect changed files
changed_files = [{"filename": f.filename, "patch": f.patch} for f in pr.get_files()]

# --- Step 1: List available Gemini models ---
list_models_url = "https://generativelanguage.googleapis.com/v1beta/models"
headers = {"X-goog-api-key": gemini_api_key}

resp = requests.get(list_models_url, headers=headers)
if resp.status_code != 200:
    print("❌ Failed to list Gemini models")
    print(resp.status_code, resp.text)
    sys.exit(1)

models_data = resp.json().get("models", [])
if not models_data:
    print("❌ No models found in Gemini response")
    sys.exit(1)

# Pick the first model that supports generateContent
selected_model = None
for m in models_data:
    if "generateContent" in m.get("supportedMethods", []):
        selected_model = m["name"]
        break

if not selected_model:
    print("❌ No models support generateContent in your API key")
    sys.exit(1)

print(f"✅ Using Gemini model: {selected_model}")

# --- Step 2: Build prompt ---
checklist_prompt = """
# PR Review Checklist
(… your structured checklist prompt …)
"""

prompt = f"""
PR Title: {pr.title}
PR Description: {pr.body}
Changed Files: {changed_files}

{checklist_prompt}
"""

# --- Step 3: Call generateContent ---
generate_url = f"https://generativelanguage.googleapis.com/v1beta/models/{selected_model}:generateContent"
payload = {"contents": [{"parts": [{"text": prompt}]}]}

response = requests.post(generate_url, headers=headers, json=payload)

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

ai_review = result["candidates"][0]["content"]["parts"][0]["text"]

# --- Step 4: Post as PR comment ---
pr.create_issue_comment(f"### 🤖 AI Code Review\n\n{ai_review}")
print("✅ AI Review posted to PR")

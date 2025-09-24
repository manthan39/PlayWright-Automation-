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
- Commit messages clear & scoped
- No sensitive data in repo
- Branching strategy followed
- PR includes summary + test evidence

10️⃣ Framework Specific Guidelines (Playwright)
- Prefer stable locators (ID > Name > CSS > XPath)
- Handle dynamic elements robustly
- Custom utilities documented

At the end, provide an overall recommendation in this exact format:

Overall Recommendation: Good to merge ✅
or
Overall Recommendation: Needs changes ❌
"""

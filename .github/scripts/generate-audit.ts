import { execSync } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';

// Config: file extensions to scan
const SCAN_EXTS = ['.ts', '.spec.ts', '.json'];

interface Contributor {
  author: string;
  timestamp: string;
  commit: string;
}

interface AuditRecord {
  file: string;
  type: 'function' | 'test' | 'json';
  name: string;
  startLine: number;
  createdBy: string;
  createdAt: string;
  lastModifiedBy: string;
  lastModifiedAt: string;
  contributors: Contributor[];
}

const PROJECT_ROOT = process.cwd();

function getAllFiles(dir: string): string[] {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  const files: string[] = [];
  for (const e of entries) {
    const full = path.join(dir, e.name);
    if (e.isDirectory()) {
      // Skip node_modules, .git, audit, scripts
      if (['node_modules', '.git', 'audit', 'scripts'].includes(e.name)) continue;
      files.push(...getAllFiles(full));
    } else {
      files.push(full);
    }
  }
  return files;
}

function filterScannable(files: string[]): string[] {
  return files.filter(f => {
    return SCAN_EXTS.some(ext => f.endsWith(ext));
  });
}

function runGitBlame(file: string): string {
  try {
    return execSync(`git blame --line-porcelain ${file}`, { encoding: 'utf-8' });
  } catch (err) {
    console.error(`git blame failed for ${file}`, err);
    return '';
  }
}

function runGitLogLine(file: string, start: number, end: number): string {
  try {
    // -L:start,end:file
    return execSync(`git log -L ${start},${end}:${file}`, { encoding: 'utf-8' });
  } catch (err) {
    // sometimes log fails if no moves
    return '';
  }
}

// A simple regex-based parser for TypeScript functions and test() blocks
function parseFile(file: string): { name: string; type: 'function' | 'test' | 'json'; startLine: number }[] {
  const content = fs.readFileSync(file, 'utf-8');
  const lines = content.split('\n');

  const records: { name: string; type: 'function' | 'test' | 'json'; startLine: number }[] = [];

  if (file.endsWith('.json')) {
    // Treat JSON as one record
    records.push({ name: path.basename(file), type: 'json', startLine: 1 });
    return records;
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

    // Match test(...) pattern
    if (line.startsWith('test(') || line.startsWith('test (`') || line.startsWith('test(`')) {
      // extract test name inside backticks or quotes
      const m = line.match(/test\((`|["'])(.*?)\1/);
      const name = m ? m[2] : `test_at_${i + 1}`;
      records.push({ name, type: 'test', startLine: i + 1 });
    }

    // Match async xyz(...) or function xyz(...) or method declarations
    // This is simplistic; for real parsing you might use ts-morph / TypeScript AST
    else {
      const asyncMatch = line.match(/^async\s+([a-zA-Z0-9_]+)\s*\(/);
      const fnMatch = line.match(/^function\s+([a-zA-Z0-9_]+)\s*\(/);
      const methodMatch = line.match(/^([a-zA-Z0-9_]+)\s*\(\)\s*{/);

      if (asyncMatch) {
        records.push({ name: asyncMatch[1], type: 'function', startLine: i + 1 });
      } else if (fnMatch) {
        records.push({ name: fnMatch[1], type: 'function', startLine: i + 1 });
      } else if (methodMatch) {
        records.push({ name: methodMatch[1], type: 'function', startLine: i + 1 });
      }
    }
  }

  return records;
}

function getFirstCommitForLine(logText: string): Contributor | null {
  // The first "commit" block in the log is the earliest
  const lines = logText.split('\n');
  for (let i = lines.length - 1; i >= 0; i--) {
    const l = lines[i];
    const cm = l.match(/^commit\s+([0-9a-fA-F]+)/);
    if (cm) {
      const commitHash = cm[1];
      // Look backward for author and date
      const authorLine = lines.slice(0, i).reverse().find(l2 => l2.startsWith('Author:'));
      const dateLine = lines.slice(0, i).reverse().find(l2 => l2.startsWith('Date:'));
      if (authorLine && dateLine) {
        const author = authorLine.replace('Author: ', '').trim();
        const timestamp = dateLine.replace('Date: ', '').trim();
        return { author, timestamp, commit: commitHash };
      }
    }
  }
  return null;
}

function getLastContributorFromBlame(blameText: string, lineNum: number): Contributor | null {
  const blocks = blameText.split('\n');
  let currentCommit = '';
  let currentAuthor = '';
  let currentTime = '';
  let curLineCount = 0;

  // we need to iterate blocks: each block starts with a commit hash line
  // then author, author-time, etc. We track which block contains the target lineNum
  let linenoCounter = 0;

  for (let i = 0; i < blocks.length; i++) {
    const l = blocks[i];
    const cm = l.match(/^([0-9a-f]{40})\s/);
    if (cm) {
      currentCommit = cm[1];
      // next lines
      const authorLine = blocks[i + 1];
      const atimeLine = blocks[i + 3];
      if (authorLine && authorLine.startsWith('author ')) {
        currentAuthor = authorLine.replace('author ', '').trim();
      }
      if (atimeLine && atimeLine.startsWith('author-time ')) {
        const ts = parseInt(atimeLine.replace('author-time ', '').trim()) * 1000;
        currentTime = new Date(ts).toISOString();
      }
      // line count lines come after a block; but simpler: count one by one
    }

    if (l.startsWith('filename ')) {
      // continue
    }

    if (l.startsWith('\t')) {
      // actual source line
      linenoCounter++;
      if (linenoCounter === lineNum) {
        return { author: currentAuthor, timestamp: currentTime, commit: currentCommit };
      }
    }
  }

  return null;
}

function generateAudit(): AuditRecord[] {
  const all = getAllFiles(PROJECT_ROOT);
  const files = filterScannable(all);

  const auditRecords: AuditRecord[] = [];

  for (const file of files) {
    const rel = path.relative(PROJECT_ROOT, file);
    const recs = parseFile(file);

    const blameText = runGitBlame(rel);

    recs.forEach(r => {
      const logText = runGitLogLine(rel, r.startLine, r.startLine);
      const first = getFirstCommitForLine(logText);
      const last = getLastContributorFromBlame(blameText, r.startLine);

      let createdBy = first ? first.author : 'unknown';
      let createdAt = first ? first.timestamp : new Date().toISOString();
      let lastBy = last ? last.author : createdBy;
      let lastAt = last ? last.timestamp : createdAt;

      // contributors: union of first + last (dedupe)
      const contribSet = new Set<string>();
      if (first) contribSet.add(first.author);
      if (last) contribSet.add(last.author);

      const contributors: Contributor[] = Array.from(contribSet).map(a => ({
        author: a,
        timestamp: a === lastBy ? lastAt : createdAt,
        commit: a === lastBy && last ? last.commit : first ? first.commit : ''
      }));

      auditRecords.push({
        file: rel,
        type: r.type,
        name: r.name,
        startLine: r.startLine,
        createdBy,
        createdAt,
        lastModifiedBy: lastBy,
        lastModifiedAt: lastAt,
        contributors
      });
    });
  }

  return auditRecords;
}

function writeAudit(audit: AuditRecord[]) {
  const out = {
    generatedAt: new Date().toISOString(),
    records: audit
  };
  if (!fs.existsSync('audit')) {
    fs.mkdirSync('audit');
  }
  fs.writeFileSync('audit/audit.json', JSON.stringify(out, null, 2), 'utf-8');
}

function generateDashboardHtml() {
  const auditObj = JSON.parse(fs.readFileSync('audit/audit.json', 'utf-8'));
  const recs: AuditRecord[] = auditObj.records;

  const authorsCount: Record<string, { created: number; modified: number }> = {};
  recs.forEach(r => {
    authorsCount[r.createdBy] = authorsCount[r.createdBy] || { created: 0, modified: 0 };
    authorsCount[r.lastModifiedBy] = authorsCount[r.lastModifiedBy] || { created: 0, modified: 0 };
    authorsCount[r.createdBy].created++;
    authorsCount[r.lastModifiedBy].modified++;
  });

  // build HTML
  let html = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Audit Dashboard</title>
  <style>
    table { border-collapse: collapse; width: 100%; }
    th, td { padding: 8px; border: 1px solid #ddd; }
    th { background: #f4f4f4; }
  </style>
</head>
<body>
  <h1>Audit Dashboard</h1>
  <h2>Leaderboard (by author)</h2>
  <table>
    <thead><tr><th>Author</th><th>Created Count</th><th>Modified Count</th></tr></thead>
    <tbody>
`;

  Object.entries(authorsCount).forEach(([author, cnt]) => {
    html += `<tr><td>${author}</td><td>${cnt.created}</td><td>${cnt.modified}</td></tr>`;
  });

  html += `
    </tbody>
  </table>

  <h2>All Records</h2>
  <table>
    <thead>
      <tr>
        <th>Type</th><th>File</th><th>Name</th><th>Start Line</th>
        <th>Created By / At</th><th>Last Modified By / At</th><th>Contributors</th>
      </tr>
    </thead>
    <tbody>
`;

  recs.forEach(r => {
    html += `<tr>
      <td>${r.type}</td>
      <td>${r.file}</td>
      <td>${r.name}</td>
      <td>${r.startLine}</td>
      <td>${r.createdBy}<br/><small>${r.createdAt}</small></td>
      <td>${r.lastModifiedBy}<br/><small>${r.lastModifiedAt}</small></td>
      <td>${r.contributors.map(c => c.author).join(', ')}</td>
    </tr>`;
  });

  html += `
    </tbody>
  </table>
</body>
</html>`;

  fs.writeFileSync('audit/dashboard.html', html, 'utf-8');
}

function main() {
  console.log('Generating audit …');
  const audit = generateAudit();
  writeAudit(audit);
  console.log('Generated audit.json');
  generateDashboardHtml();
  console.log('Generated dashboard.html');
}

main();
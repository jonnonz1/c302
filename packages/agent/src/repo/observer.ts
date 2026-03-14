import { exec } from 'node:child_process';
import { resolve } from 'node:path';
import type { RepoSnapshot, TestResults, TestDetail, GitDiffStat } from '../types.js';

/**
 * Execute a command and return stdout. Resolves with empty string on error.
 */
function run(command: string, cwd: string): Promise<string> {
  return new Promise((res) => {
    exec(command, { cwd, encoding: 'utf-8', maxBuffer: 1024 * 1024, timeout: 60000 }, (err, stdout, stderr) => {
      if (err) {
        res((stdout || '') + (stderr || ''));
      } else {
        res(stdout || '');
      }
    });
  });
}

/**
 * Parse vitest JSON reporter output into TestResults.
 */
function parseTestResults(raw: string): TestResults | null {
  try {
    const json = JSON.parse(raw);
    const details: TestDetail[] = [];
    let passed = 0;
    let failed = 0;
    let skipped = 0;

    for (const file of json.testResults ?? []) {
      for (const test of file.assertionResults ?? []) {
        const status = test.status === 'passed' ? 'passed'
          : test.status === 'failed' ? 'failed'
          : 'skipped';

        if (status === 'passed') passed++;
        else if (status === 'failed') failed++;
        else skipped++;

        details.push({
          name: test.fullName ?? test.title ?? 'unknown',
          status,
          error_message: test.failureMessages?.join('\n') ?? null,
        });
      }
    }

    const total = passed + failed + skipped;
    return {
      total,
      passed,
      failed,
      skipped,
      pass_rate: total > 0 ? passed / total : 0,
      details,
    };
  } catch {
    return null;
  }
}

/**
 * Parse git diff --stat output into GitDiffStat.
 */
function parseDiffStat(raw: string): GitDiffStat | null {
  if (!raw.trim()) return null;

  const lines = raw.trim().split('\n');
  const summaryLine = lines[lines.length - 1];
  const filesMatch = summaryLine.match(/(\d+)\s+files?\s+changed/);
  const insertMatch = summaryLine.match(/(\d+)\s+insertions?\(\+\)/);
  const deleteMatch = summaryLine.match(/(\d+)\s+deletions?\(-\)/);

  return {
    files_changed: filesMatch ? parseInt(filesMatch[1], 10) : 0,
    insertions: insertMatch ? parseInt(insertMatch[1], 10) : 0,
    deletions: deleteMatch ? parseInt(deleteMatch[1], 10) : 0,
  };
}

/**
 * Count TypeScript errors by running tsc --noEmit.
 */
async function countLintErrors(repoPath: string): Promise<number> {
  const output = await run('npx tsc --noEmit 2>&1', repoPath);
  if (!output.trim()) return 0;
  const errorLines = output.split('\n').filter((line) => /error TS\d+/.test(line));
  return errorLines.length;
}

/**
 * Check if the project builds successfully.
 */
async function checkBuild(repoPath: string): Promise<boolean> {
  const output = await run('npm run build 2>&1', repoPath);
  return !output.includes('error');
}

/**
 * Take a snapshot of the repository state.
 */
export async function snapshot(repoPath: string): Promise<RepoSnapshot> {
  const abs = resolve(repoPath);

  const [testRaw, lintErrors, buildOk, modifiedRaw, diffStatRaw] = await Promise.all([
    run('npx vitest run --reporter=json 2>/dev/null', abs),
    countLintErrors(abs),
    checkBuild(abs),
    run('git diff --name-only', abs),
    run('git diff --stat', abs),
  ]);

  return {
    test_results: parseTestResults(testRaw),
    lint_errors: lintErrors,
    build_ok: buildOk,
    files_modified: modifiedRaw.trim().split('\n').filter(Boolean),
    git_diff_stat: parseDiffStat(diffStatRaw),
  };
}

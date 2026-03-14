import { execSync } from 'node:child_process';
import { readFileSync, writeFileSync, readdirSync, statSync } from 'node:fs';
import { resolve, relative } from 'node:path';

/**
 * Validate that a resolved path is within the allowed repo path.
 * Throws if path traversal is detected.
 */
function assertWithinRepo(filePath: string, repoPath: string): string {
  const resolved = resolve(repoPath, filePath);
  const resolvedRepo = resolve(repoPath);
  if (!resolved.startsWith(resolvedRepo + '/') && resolved !== resolvedRepo) {
    throw new Error(`Path traversal denied: ${filePath}`);
  }
  return resolved;
}

/**
 * Read a file's contents and return as string.
 */
export function readFile(filePath: string, repoPath: string): Promise<string> {
  const abs = assertWithinRepo(filePath, repoPath);
  try {
    return Promise.resolve(readFileSync(abs, 'utf-8'));
  } catch (err) {
    return Promise.resolve(`Error reading ${filePath}: ${(err as Error).message}`);
  }
}

/**
 * Write content to a file. Returns confirmation message.
 */
export function writeFile(filePath: string, content: string, repoPath: string): Promise<string> {
  const abs = assertWithinRepo(filePath, repoPath);
  try {
    writeFileSync(abs, content, 'utf-8');
    return Promise.resolve(`Wrote ${content.length} bytes to ${filePath}`);
  } catch (err) {
    return Promise.resolve(`Error writing ${filePath}: ${(err as Error).message}`);
  }
}

/**
 * Search code in the repo using grep. Returns matching lines limited by maxResults.
 */
export function searchCode(query: string, repoPath: string, maxResults: number = 10): Promise<string> {
  const abs = resolve(repoPath);
  try {
    const result = execSync(
      `grep -rn --include='*.ts' --include='*.js' --include='*.json' ${JSON.stringify(query)} .`,
      { cwd: abs, encoding: 'utf-8', maxBuffer: 1024 * 1024, timeout: 10000 },
    );
    if (!result) return Promise.resolve('No matches found.');
    const lines = result.trim().split('\n');
    const limited = lines.slice(0, maxResults);
    const suffix = lines.length > maxResults ? `\n... (${lines.length - maxResults} more matches)` : '';
    return Promise.resolve(limited.join('\n') + suffix);
  } catch {
    return Promise.resolve('No matches found.');
  }
}

/**
 * Run a shell command in the repo directory. Returns stdout+stderr.
 */
export function runCommand(command: string, repoPath: string): Promise<string> {
  const abs = resolve(repoPath);
  try {
    const result = execSync(command, {
      cwd: abs,
      encoding: 'utf-8',
      maxBuffer: 1024 * 1024,
      timeout: 30000,
      stdio: ['pipe', 'pipe', 'pipe'],
    });
    return Promise.resolve(result);
  } catch (err) {
    const execErr = err as { stdout?: string; stderr?: string; message: string };
    return Promise.resolve(
      (execErr.stdout || '') + (execErr.stderr || '') || execErr.message,
    );
  }
}

/**
 * List files in a directory within the repo. Returns newline-separated listing.
 */
export function listFiles(dirPath: string, repoPath: string): Promise<string> {
  const abs = assertWithinRepo(dirPath, repoPath);
  try {
    const entries = readdirSync(abs);
    const lines = entries.map((entry) => {
      const fullPath = resolve(abs, entry);
      const stat = statSync(fullPath);
      const rel = relative(resolve(repoPath), fullPath);
      return stat.isDirectory() ? `${rel}/` : rel;
    });
    return Promise.resolve(lines.join('\n') || 'Empty directory.');
  } catch (err) {
    return Promise.resolve(`Error listing ${dirPath}: ${(err as Error).message}`);
  }
}

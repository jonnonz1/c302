import Anthropic from '@anthropic-ai/sdk';
import type { AgentConfig, ToolDefinition } from '../surface-applicator.js';
import type { AgentAction, AgentMode, Tool, ToolCall, TickContext } from '../types.js';
import type { TickEventBus } from '../events.js';
import { readFile, writeFile, searchCode, runCommand, listFiles } from './tools.js';

export const DEFAULT_MODEL = 'claude-sonnet-4-20250514';

/**
 * Mode-specific user prompts that defer behavioral framing to the system prompt.
 */
/**
 * Mode-specific user prompts. When repo files are pre-loaded into the system
 * prompt, the PRELOADED variants tell the agent not to re-read them.
 */
const USER_PROMPTS: Record<AgentMode, string> = {
  diagnose: 'Examine the repository. Read files and tests to understand what is broken and why. Do not make changes yet.',
  search: 'Search the codebase for code relevant to the failing tests. Look at imports, types, and related modules.',
  'edit-small': 'Make a small, targeted code change to fix or progress toward fixing the failing tests.',
  'edit-large': 'Implement the missing functionality needed to make the failing tests pass.',
  'run-tests': 'Run the test suite with `npm test` and report which tests pass and which fail.',
  reflect: 'Review what you have done so far and what the test results tell you. Plan your next step.',
  stop: 'The task is complete.',
};

const USER_PROMPTS_PRELOADED: Record<AgentMode, string> = {
  diagnose: 'The repository source files are provided above in your context. Analyze them to understand what is broken and why. Do not make changes yet. Do not re-read files you already have.',
  search: 'The repository source files are provided above in your context. Identify the code relevant to the failing tests. Do not re-read files you already have.',
  'edit-small': 'The repository source files are provided above in your context. Make a small, targeted code change to fix or progress toward fixing the failing tests. Write the fix directly — do not re-read files you already have.',
  'edit-large': 'The repository source files are provided above in your context. Implement the missing functionality needed to make the failing tests pass. Write the fix directly — do not re-read files you already have.',
  'run-tests': 'Run the test suite with `npm test` and report which tests pass and which fail.',
  reflect: 'Review what you have done so far and what the test results tell you. Plan your next step.',
  stop: 'The task is complete.',
};

type ContentBlock = Anthropic.Messages.ContentBlock;
type ToolUseBlock = Anthropic.Messages.ToolUseBlock;
type MessageParam = Anthropic.Messages.MessageParam;

/**
 * Dispatch a tool call to the appropriate tool implementation.
 */
async function dispatchTool(
  name: string,
  input: Record<string, unknown>,
  repoPath: string,
  searchBreadth: number,
): Promise<string> {
  switch (name) {
    case 'read_file':
      return readFile(input.path as string, repoPath);
    case 'write_file':
      return writeFile(input.path as string, input.content as string, repoPath);
    case 'search_code':
      return searchCode(input.query as string, repoPath, searchBreadth);
    case 'run_command':
      return runCommand(input.command as string, repoPath);
    case 'list_files':
      return listFiles((input.path as string) || '.', repoPath);
    default:
      return `Unknown tool: ${name}`;
  }
}

const TOOL_RESULT_MAX_CHARS = 8192;

/**
 * Truncate a tool result string to stay within the character budget.
 */
function truncateResult(result: string): string {
  if (result.length <= TOOL_RESULT_MAX_CHARS) return result;
  return result.slice(0, TOOL_RESULT_MAX_CHARS) +
    `\n... (truncated, ${result.length} chars total)`;
}

/**
 * Check if a content block is a tool use block.
 */
function isToolUse(block: ContentBlock): block is ToolUseBlock {
  return block.type === 'tool_use';
}

/**
 * Extract text from content blocks.
 */
function extractText(blocks: ContentBlock[]): string {
  return blocks
    .filter((b): b is Anthropic.Messages.TextBlock => b.type === 'text')
    .map((b) => b.text)
    .join('\n');
}

const CONTEXT_MAX_HISTORY = 5;
const CONTEXT_DESCRIPTION_MAX = 100;
const CONTEXT_MAX_CHARS = 500;

/**
 * Build a context string from tick history for injection into the system prompt.
 */
export function buildContextString(context: TickContext): string {
  const header = `--- Tick Context ---\nTick ${context.tick} of ${context.maxTicks}.`;

  if (context.history.length === 0) {
    return `${header}\nNo previous actions.`;
  }

  const recent = context.history.slice(-CONTEXT_MAX_HISTORY);
  const lines = recent.map((entry) => {
    const desc = entry.description.length > CONTEXT_DESCRIPTION_MAX
      ? entry.description.slice(0, CONTEXT_DESCRIPTION_MAX - 3) + '...'
      : entry.description;
    const files = entry.filesWritten.length > 0
      ? `Wrote ${entry.filesWritten.join(', ')}. `
      : '';
    const tests = entry.testPassRate !== null
      ? `Tests: ${Math.round(entry.testPassRate * 100)}% passing. `
      : '';
    return `- Tick ${entry.tick} (${entry.mode}): ${files}${tests}Reward: ${entry.reward.toFixed(3)}${desc ? ` -- ${desc}` : ''}`;
  });

  let result = `${header}\nRecent history:`;
  for (const line of lines) {
    const candidate = `${result}\n${line}`;
    if (candidate.length > CONTEXT_MAX_CHARS) break;
    result = candidate;
  }

  return result;
}

/**
 * Execute one tick of LLM agent work. Handles multi-turn tool use.
 *
 * When repoContext is provided, the source files are pre-loaded into the
 * system prompt as a cached prefix. This eliminates redundant file reads
 * and enables Anthropic prompt caching (requires >=1024 tokens).
 */
export async function execute(
  config: AgentConfig,
  repoPath: string,
  mode: AgentMode,
  model: string = DEFAULT_MODEL,
  bus?: TickEventBus,
  tick?: number,
  context?: TickContext,
  repoContext?: string,
): Promise<AgentAction> {
  const client = new Anthropic();

  const modePrompt = context
    ? `${config.systemPrompt}\n\n${buildContextString(context)}`
    : config.systemPrompt;

  const toolCalls: ToolCall[] = [];
  const filesRead: string[] = [];
  const filesWritten: string[] = [];
  let description = '';

  const prompts = repoContext ? USER_PROMPTS_PRELOADED : USER_PROMPTS;
  const messages: MessageParam[] = [
    { role: 'user', content: prompts[mode] },
  ];

  const toolDefs = config.tools.map((t: ToolDefinition) => ({
    name: t.name,
    description: t.description,
    input_schema: t.input_schema as Anthropic.Messages.Tool['input_schema'],
  }));

  let iterations = 0;
  // Fixed iteration count for all controllers (Phase 2 design).
  // Decoupled from token_budget to remove the iteration-budget confound
  // discovered in Phase 1 (see PHASE-1-REPORT.md Section 4.4).
  // token_budget now controls only max_tokens per API call (response depth).
  const maxIterations = 6;
  let totalInputTokens = 0;
  let totalOutputTokens = 0;
  let totalCacheReadTokens = 0;

  // Build system prompt: if repoContext is provided, use a two-part structure
  // with cache_control on the stable file prefix for cross-tick caching.
  const systemBlocks: Anthropic.Messages.TextBlockParam[] = repoContext
    ? [
        { type: 'text', text: repoContext, cache_control: { type: 'ephemeral' } },
        { type: 'text', text: modePrompt },
      ]
    : [{ type: 'text', text: modePrompt }];

  if (tick !== undefined) {
    console.log(`  [cost] tick=${tick} mode=${mode} budget=${config.maxTokens} maxIters=${maxIterations} cached=${!!repoContext}`);
  }

  while (iterations < maxIterations) {
    iterations++;

    const response = await client.messages.create({
      model,
      max_tokens: config.maxTokens,
      temperature: config.temperature,
      system: systemBlocks,
      tools: toolDefs.length > 0 ? toolDefs : undefined,
      messages,
    });

    const inputTokens = response.usage?.input_tokens ?? 0;
    const outputTokens = response.usage?.output_tokens ?? 0;
    totalInputTokens += inputTokens;
    totalOutputTokens += outputTokens;

    const cacheCreation = (response.usage as unknown as Record<string, number>)?.cache_creation_input_tokens ?? 0;
    const cacheRead = (response.usage as unknown as Record<string, number>)?.cache_read_input_tokens ?? 0;
    totalCacheReadTokens += cacheRead;

    if (tick !== undefined) {
      console.log(`  [cost] tick=${tick} iter=${iterations}/${maxIterations} in=${inputTokens} out=${outputTokens} cached=${cacheRead} cumIn=${totalInputTokens} cumOut=${totalOutputTokens}`);
    }

    const textContent = extractText(response.content);
    if (textContent) {
      description += (description ? '\n' : '') + textContent;
      if (bus && tick !== undefined) {
        bus.emit('tick:llm-text', { tick, text: textContent });
      }
    }

    const toolUseBlocks = response.content.filter(isToolUse);

    if (toolUseBlocks.length === 0 || response.stop_reason !== 'tool_use') {
      break;
    }

    messages.push({ role: 'assistant', content: response.content });

    const toolResults: Anthropic.Messages.ToolResultBlockParam[] = [];

    for (const block of toolUseBlocks) {
      const input = block.input as Record<string, unknown>;
      const result = await dispatchTool(block.name, input, repoPath, config.searchBreadth);

      const toolName = block.name as Tool;
      toolCalls.push({ tool: toolName, args: input, result });

      if (bus && tick !== undefined) {
        bus.emit('tick:tool-call', { tick, tool: toolName, args: input, result });
      }

      if (block.name === 'read_file' && input.path) {
        filesRead.push(input.path as string);
      }
      if (block.name === 'write_file' && input.path) {
        filesWritten.push(input.path as string);
      }

      toolResults.push({
        type: 'tool_result',
        tool_use_id: block.id,
        content: truncateResult(result),
      });
    }

    messages.push({ role: 'user', content: toolResults });
  }

  if (tick !== undefined) {
    // Sonnet: $3/MTok uncached input, $0.30/MTok cached input, $15/MTok output
    // Note: input_tokens from API = uncached only; cached reported separately
    const estCost = (totalInputTokens * 3 + totalCacheReadTokens * 0.3 + totalOutputTokens * 15) / 1_000_000;
    console.log(`  [cost] tick=${tick} DONE iters=${iterations} in=${totalInputTokens} cached=${totalCacheReadTokens} out=${totalOutputTokens} est=$${estCost.toFixed(4)}`);
  }

  return {
    mode,
    description: description || 'No response from agent.',
    tool_calls: toolCalls,
    files_read: filesRead,
    files_written: filesWritten,
    timestamp: new Date().toISOString(),
  };
}

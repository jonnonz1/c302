import Anthropic from '@anthropic-ai/sdk';
import type { AgentConfig, ToolDefinition } from '../surface-applicator.js';
import type { AgentAction, AgentMode, Tool, ToolCall, TickContext } from '../types.js';
import type { TickEventBus } from '../events.js';
import { readFile, writeFile, searchCode, runCommand, listFiles } from './tools.js';

export const DEFAULT_MODEL = 'claude-sonnet-4-20250514';

/**
 * Mode-specific user prompts that defer behavioral framing to the system prompt.
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
 */
export async function execute(
  config: AgentConfig,
  repoPath: string,
  mode: AgentMode,
  model: string = DEFAULT_MODEL,
  bus?: TickEventBus,
  tick?: number,
  context?: TickContext,
): Promise<AgentAction> {
  const client = new Anthropic();

  const systemPrompt = context
    ? `${config.systemPrompt}\n\n${buildContextString(context)}`
    : config.systemPrompt;

  const toolCalls: ToolCall[] = [];
  const filesRead: string[] = [];
  const filesWritten: string[] = [];
  let description = '';

  const messages: MessageParam[] = [
    { role: 'user', content: USER_PROMPTS[mode] },
  ];

  const toolDefs = config.tools.map((t: ToolDefinition) => ({
    name: t.name,
    description: t.description,
    input_schema: t.input_schema as Anthropic.Messages.Tool['input_schema'],
  }));

  let iterations = 0;
  const maxIterations = 10;

  while (iterations < maxIterations) {
    iterations++;

    const response = await client.messages.create({
      model,
      max_tokens: config.maxTokens,
      temperature: config.temperature,
      system: [
        {
          type: 'text',
          text: systemPrompt,
          cache_control: { type: 'ephemeral' },
        },
      ],
      tools: toolDefs.length > 0 ? toolDefs : undefined,
      messages,
    });

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
        content: result,
      });
    }

    messages.push({ role: 'user', content: toolResults });
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

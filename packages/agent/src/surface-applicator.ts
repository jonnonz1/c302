import type { ControlSurface, Tool, TickContext } from './types.js';
import { PROMPTS, aggressionDirective } from './coding/prompts.js';

export interface ToolDefinition {
  name: string;
  description: string;
  input_schema: {
    type: 'object';
    properties: Record<string, { type: string; description: string }>;
    required: string[];
  };
}

export interface AgentConfig {
  systemPrompt: string;
  temperature: number;
  maxTokens: number;
  tools: ToolDefinition[];
  searchBreadth: number;
  context?: TickContext;
}

const TOOL_DEFINITIONS: Record<Tool, ToolDefinition> = {
  read_file: {
    name: 'read_file',
    description: 'Read the contents of a file at the given path relative to the repo root.',
    input_schema: {
      type: 'object',
      properties: {
        path: { type: 'string', description: 'File path relative to repo root' },
      },
      required: ['path'],
    },
  },
  write_file: {
    name: 'write_file',
    description: 'Write content to a file at the given path relative to the repo root.',
    input_schema: {
      type: 'object',
      properties: {
        path: { type: 'string', description: 'File path relative to repo root' },
        content: { type: 'string', description: 'File content to write' },
      },
      required: ['path', 'content'],
    },
  },
  search_code: {
    name: 'search_code',
    description: 'Search for a text pattern across the codebase. Returns matching lines.',
    input_schema: {
      type: 'object',
      properties: {
        query: { type: 'string', description: 'Search query string' },
      },
      required: ['query'],
    },
  },
  run_command: {
    name: 'run_command',
    description: 'Run a shell command in the repo directory. Returns stdout and stderr.',
    input_schema: {
      type: 'object',
      properties: {
        command: { type: 'string', description: 'Shell command to execute' },
      },
      required: ['command'],
    },
  },
  list_files: {
    name: 'list_files',
    description: 'List files and directories at the given path relative to the repo root.',
    input_schema: {
      type: 'object',
      properties: {
        path: { type: 'string', description: 'Directory path relative to repo root' },
      },
      required: ['path'],
    },
  },
};

/**
 * Translate a ControlSurface into Claude API configuration.
 */
export function apply(surface: ControlSurface, context?: TickContext): AgentConfig {
  const basePrompt = PROMPTS[surface.mode];
  const directive = aggressionDirective(surface.aggression);
  const systemPrompt = `${basePrompt}\n\n${directive}`;

  const tools = surface.allowed_tools.map((t) => TOOL_DEFINITIONS[t]);

  return {
    systemPrompt,
    temperature: surface.temperature,
    maxTokens: surface.token_budget,
    tools,
    searchBreadth: surface.search_breadth,
    context,
  };
}

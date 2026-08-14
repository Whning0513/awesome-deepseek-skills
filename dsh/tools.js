import { findEntry, publicEntry, searchEntries } from './catalog.js'
import { installEntry } from './install.js'

const jsonOutput = {
  schema: { type: 'json' },
  render: (_args, value) => [{ type: 'text', text: JSON.stringify(value, null, 2) }],
}

export function createToolDefinitions(defineTool) {
  return [
    defineTool({
      name: 'deepseek_skills_list',
      description:
        'Read the small, commit-pinned Awesome DeepSeek Skills catalog bundled with this plugin. '
        + 'Optionally filter by text or category. This is offline and does not install or execute anything.',
      parameters: {
        query: {
          type: 'string',
          description: 'Optional case-insensitive text matched against id, name, description, and category.',
        },
        category: {
          type: 'string',
          enum: ['deepseek', 'development', 'design', 'productivity', 'security'],
          description: 'Optional exact catalog category.',
        },
      },
      output: jsonOutput,
      timeoutMs: 10_000,
      isConcurrencySafe: () => true,
      async execute(args) {
        const entries = await searchEntries({ query: args.query, category: args.category })
        return { count: entries.length, entries: entries.map(publicEntry) }
      },
    }),
    defineTool({
      name: 'deepseek_skill_install',
      description:
        'Only use after the user explicitly asks to install the exact catalog id. '
        + 'Install that skill at its pinned commit into the current DSH project. '
        + 'This fetches from the network and writes either .agents/skills or .dsh/skills. '
        + 'It refuses overwrites and symbolic links, and never executes scripts from the skill.',
      parameters: {
        id: {
          type: 'string',
          required: true,
          description: 'Exact catalog id returned by deepseek_skills_list.',
        },
        scope: {
          type: 'string',
          enum: ['agents', 'dsh'],
          description: 'Project skill root; agents means .agents/skills and dsh means .dsh/skills. Defaults to agents.',
        },
      },
      output: jsonOutput,
      timeoutMs: 240_000,
      async execute(args, exec) {
        const projectRoot = exec.agent?.session.header.cwd
        const entry = await findEntry(args.id)
        return installEntry(entry, {
          projectRoot,
          scope: args.scope ?? 'agents',
          signal: exec.signal,
        })
      },
    }),
  ]
}

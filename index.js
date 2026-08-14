import { defineTool } from '@deepseek-ai/dsh-tools'

import { createToolDefinitions } from './dsh/tools.js'

export const name = 'dsh-awesome-deepseek-skills'
export const inject = ['tools']

export function apply(ctx) {
  for (const definition of createToolDefinitions(defineTool)) {
    ctx.tools.register(definition)
  }
}

import { readFile, readdir } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const PLUGIN_ROOT = dirname(dirname(fileURLToPath(import.meta.url)))
const CATALOG_DIR = join(PLUGIN_ROOT, 'catalog', 'skills')

export async function loadEntries() {
  const names = (await readdir(CATALOG_DIR))
    .filter(name => name.endsWith('.json'))
    .sort((left, right) => left.localeCompare(right, 'en'))
  return Promise.all(names.map(async name => {
    const entry = JSON.parse(await readFile(join(CATALOG_DIR, name), 'utf8'))
    assertPackagedEntry(entry, name)
    return entry
  }))
}

export async function findEntry(id) {
  const normalized = id.toLowerCase()
  const entry = (await loadEntries()).find(candidate => candidate.id.toLowerCase() === normalized)
  if (entry === undefined) throw new Error(`unknown skill id: ${id}`)
  return entry
}

export async function searchEntries({ query, category } = {}) {
  const needle = query?.trim().toLowerCase()
  return (await loadEntries()).filter(entry => {
    if (category !== undefined && entry.category !== category) return false
    if (!needle) return true
    return [entry.id, entry.name, entry.description, entry.category]
      .some(value => value.toLowerCase().includes(needle))
  })
}

export function publicEntry(entry) {
  return {
    id: entry.id,
    name: entry.name,
    description: entry.description,
    category: entry.category,
    maturity: entry.source.maturity,
    repository: entry.source.repository,
    commit: entry.source.commit,
    path: entry.source.path,
    license: entry.license.spdx,
    risk: entry.risk,
  }
}

function assertPackagedEntry(entry, filename) {
  if (entry === null || typeof entry !== 'object' || Array.isArray(entry)) {
    throw new Error(`invalid packaged catalog entry: ${filename}`)
  }
  for (const key of ['id', 'name', 'description', 'category']) {
    if (typeof entry[key] !== 'string') {
      throw new Error(`invalid packaged catalog entry ${filename}: missing ${key}`)
    }
  }
  if (entry.source === null || typeof entry.source !== 'object') {
    throw new Error(`invalid packaged catalog entry ${filename}: missing source`)
  }
  for (const key of ['repository', 'commit', 'path', 'maturity']) {
    if (typeof entry.source[key] !== 'string') {
      throw new Error(`invalid packaged catalog entry ${filename}: missing source.${key}`)
    }
  }
}

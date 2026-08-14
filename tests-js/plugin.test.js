import assert from 'node:assert/strict'
import { execFile } from 'node:child_process'
import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { pathToFileURL } from 'node:url'
import { promisify } from 'node:util'
import test from 'node:test'

import { findEntry, loadEntries, searchEntries } from '../dsh/catalog.js'
import { installEntry } from '../dsh/install.js'
import { createToolDefinitions } from '../dsh/tools.js'

const run = promisify(execFile)

test('packaged catalog can be listed and filtered offline', async () => {
  const entries = await loadEntries()
  assert.equal(entries.length, 8)
  assert.ok(entries.every(entry => /^[0-9a-f]{40}$/u.test(entry.source.commit)))

  const deepseek = await searchEntries({ category: 'deepseek' })
  assert.ok(deepseek.length >= 2)
  assert.ok(deepseek.every(entry => entry.category === 'deepseek'))
  assert.equal(
    (await findEntry('WHNING0513/DEEPSEEK-SKILL-DOCTOR/DEEPSEEK-SKILL-DOCTOR')).name,
    'deepseek-skill-doctor',
  )
})

test('DSH definitions expose one offline reader and one project installer', async () => {
  const definitions = createToolDefinitions(value => value)
  assert.deepEqual(
    definitions.map(definition => definition.name),
    ['deepseek_skills_list', 'deepseek_skill_install'],
  )
  assert.equal(definitions[0].isConcurrencySafe(), true)
  assert.equal(definitions[1].isConcurrencySafe, undefined)

  const result = await definitions[0].execute({ query: 'protocol' })
  assert.ok(result.entries.some(entry => entry.name === 'deepseek-protocol-doctor'))
})

test('installer fetches an exact commit, writes provenance, and refuses overwrite', async t => {
  const temporaryRoot = await mkdtemp(join(tmpdir(), 'awesome-deepseek-skills-test-'))
  t.after(() => rm(temporaryRoot, { recursive: true, force: true, maxRetries: 3 }))
  const repository = join(temporaryRoot, 'source')
  const bundle = join(repository, 'skills', 'portable-example')
  const secondBundle = join(repository, 'skills', 'portable-second')
  const project = join(temporaryRoot, 'project')
  await mkdir(bundle, { recursive: true })
  await mkdir(secondBundle, { recursive: true })
  await mkdir(project)
  await writeFile(
    join(bundle, 'SKILL.md'),
    '---\nname: portable-example\ndescription: A small fixture skill used only by the installer test.\n---\n\n# Portable example\n',
  )
  await writeFile(
    join(secondBundle, 'SKILL.md'),
    '---\nname: portable-second\ndescription: A second fixture used to exercise lock updates.\n---\n\n# Portable second\n',
  )
  await run('git', ['init', '-q', repository])
  await run('git', ['-C', repository, 'config', 'user.name', 'Fixture'])
  await run('git', ['-C', repository, 'config', 'user.email', 'fixture@example.invalid'])
  await run('git', ['-C', repository, 'add', '.'])
  await run('git', ['-C', repository, 'commit', '-q', '-m', 'fixture'])
  const { stdout } = await run('git', ['-C', repository, 'rev-parse', 'HEAD'])
  const commit = stdout.trim()
  const entry = {
    id: 'fixture/source/portable-example',
    name: 'portable-example',
    source: {
      repository: pathToFileURL(repository).href,
      commit,
      path: 'skills/portable-example',
    },
  }
  const secondEntry = {
    ...entry,
    id: 'fixture/source/portable-second',
    name: 'portable-second',
    source: { ...entry.source, path: 'skills/portable-second' },
  }

  const result = await installEntry(entry, {
    projectRoot: project,
    signal: new AbortController().signal,
  })
  assert.equal(result.commit, commit)
  assert.match(await readFile(join(result.destination, 'SKILL.md'), 'utf8'), /Portable example/u)
  await installEntry(secondEntry, { projectRoot: project })
  const lock = JSON.parse(
    await readFile(join(project, '.agents', 'skills', '.deepseek-skills.lock.json'), 'utf8'),
  )
  assert.equal(lock.skills[entry.id].commit, commit)
  assert.equal(lock.skills[secondEntry.id].commit, commit)

  await assert.rejects(
    installEntry(entry, { projectRoot: project }),
    /refusing to overwrite/u,
  )
})

test('installer rejects an already-aborted call before creating project files', async () => {
  const controller = new AbortController()
  controller.abort()
  await assert.rejects(
    installEntry({ name: 'unused' }, { projectRoot: '.', signal: controller.signal }),
    error => error.name === 'AbortError',
  )
})

test('package advertises a source-installable DSH bundle', async () => {
  const manifest = JSON.parse(await readFile(new URL('../package.json', import.meta.url), 'utf8'))
  assert.equal(manifest.name, 'dsh-awesome-deepseek-skills')
  assert.equal(manifest.dsh.bundle.patch, './cordis.patch.yml')
  assert.ok(manifest.files.includes('catalog/skills/'))
})

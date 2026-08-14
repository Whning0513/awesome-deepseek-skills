import { spawn } from 'node:child_process'
import {
  access,
  cp,
  lstat,
  mkdir,
  mkdtemp,
  readFile,
  readdir,
  realpath,
  rename,
  rm,
  writeFile,
} from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { isAbsolute, join, relative, resolve, sep } from 'node:path'

const MAX_GIT_OUTPUT_BYTES = 1024 * 1024
const TARGETS = {
  agents: ['.agents', 'skills'],
  dsh: ['.dsh', 'skills'],
}

export async function installEntry(entry, { projectRoot, scope = 'agents', signal } = {}) {
  if (typeof projectRoot !== 'string' || projectRoot.length === 0) {
    throw new Error('a DSH session workspace is required for installation')
  }
  if (!(scope in TARGETS)) throw new Error(`unsupported install scope: ${scope}`)
  throwIfAborted(signal)

  const root = await realpath(resolve(projectRoot))
  const target = resolve(root, ...TARGETS[scope])
  assertWithin(root, target, 'skill target')
  await rejectExistingSymlinks(root, target)
  const destination = resolve(target, entry.name)
  assertWithin(target, destination, 'skill destination')
  if (await pathExists(destination)) {
    throw new Error(`refusing to overwrite ${destination}`)
  }

  const lockPath = join(target, '.deepseek-skills.lock.json')
  const lock = await readLock(lockPath)
  const temporaryRoot = await mkdtemp(join(tmpdir(), 'deepseek-skill-install-'))
  const checkout = join(temporaryRoot, 'repo')
  const emptyHooks = join(temporaryRoot, 'empty-hooks')
  let reserved = false

  try {
    await mkdir(emptyHooks)
    await checkoutEntry(entry.source, checkout, emptyHooks, signal)
    const bundle = resolve(checkout, entry.source.path)
    assertWithin(checkout, bundle, 'catalog source')
    await access(join(bundle, 'SKILL.md'))
    await rejectSymbolicLinks(bundle)
    throwIfAborted(signal)

    await mkdir(target, { recursive: true })
    await mkdir(destination)
    reserved = true
    await copyBundle(bundle, destination)
    throwIfAborted(signal)

    lock.skills[entry.id] = {
      name: entry.name,
      repository: entry.source.repository,
      commit: entry.source.commit,
      path: entry.source.path,
    }
    await writeLock(lockPath, lock)
    return {
      id: entry.id,
      name: entry.name,
      scope,
      destination,
      commit: entry.source.commit,
    }
  } catch (error) {
    if (reserved) await rm(destination, { recursive: true, force: true, maxRetries: 3 })
    throw error
  } finally {
    await rm(temporaryRoot, { recursive: true, force: true, maxRetries: 3 })
  }
}

async function checkoutEntry(source, checkout, emptyHooks, signal) {
  const hooksPath = emptyHooks.split(sep).join('/')
  await runGit(['init', '-q', checkout], signal)
  await runGit(['-C', checkout, 'remote', 'add', 'origin', repositoryRemote(source.repository)], signal)
  await runGit(['-C', checkout, 'sparse-checkout', 'init', '--cone'], signal)
  await runGit(['-C', checkout, 'sparse-checkout', 'set', source.path], signal)
  await runGit([
    '-C', checkout,
    '-c', `core.hooksPath=${hooksPath}`,
    'fetch', '--depth=1', '--filter=blob:none', 'origin', source.commit,
  ], signal, 180_000)
  await runGit([
    '-C', checkout,
    '-c', `core.hooksPath=${hooksPath}`,
    'checkout', '--detach', 'FETCH_HEAD',
  ], signal)
  const actual = (await runGit(['-C', checkout, 'rev-parse', 'HEAD'], signal)).trim()
  if (actual !== source.commit) {
    throw new Error(`expected ${source.commit}, checked out ${actual}`)
  }
}

function repositoryRemote(repository) {
  return /^https:\/\/github\.com\/[^/]+\/[^/]+$/u.test(repository)
    ? `${repository}.git`
    : repository
}

function runGit(args, signal, timeoutMs = 60_000) {
  throwIfAborted(signal)
  return new Promise((resolvePromise, rejectPromise) => {
    const child = spawn('git', args, {
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
    })
    const stdout = []
    const stderr = []
    let outputBytes = 0
    let settled = false
    let timedOut = false

    const finish = callback => {
      if (settled) return
      settled = true
      clearTimeout(timer)
      signal?.removeEventListener('abort', onAbort)
      callback()
    }
    const onAbort = () => child.kill('SIGTERM')
    const timer = setTimeout(() => {
      timedOut = true
      child.kill('SIGTERM')
    }, timeoutMs)
    signal?.addEventListener('abort', onAbort, { once: true })

    child.once('error', error => finish(() => {
      if (error.code === 'ENOENT') {
        rejectPromise(new Error('git is required to install catalog entries'))
      } else {
        rejectPromise(error)
      }
    }))
    child.stdout.on('data', chunk => {
      outputBytes += chunk.length
      if (outputBytes <= MAX_GIT_OUTPUT_BYTES) stdout.push(chunk)
    })
    child.stderr.on('data', chunk => {
      outputBytes += chunk.length
      if (outputBytes <= MAX_GIT_OUTPUT_BYTES) stderr.push(chunk)
    })
    child.once('close', code => finish(() => {
      if (signal?.aborted) {
        rejectPromise(abortError())
        return
      }
      if (timedOut) {
        rejectPromise(new Error(`git ${args[0]} timed out after ${timeoutMs} ms`))
        return
      }
      if (outputBytes > MAX_GIT_OUTPUT_BYTES) {
        rejectPromise(new Error('git output exceeded 1 MiB'))
        return
      }
      const output = Buffer.concat(stdout).toString('utf8')
      const errorOutput = Buffer.concat(stderr).toString('utf8').trim()
      if (code !== 0) {
        rejectPromise(new Error(`git ${args[0]} failed (exit ${code}): ${errorOutput || 'no error output'}`))
        return
      }
      resolvePromise(output)
    }))
  })
}

async function rejectSymbolicLinks(root) {
  const rootInfo = await lstat(root)
  if (rootInfo.isSymbolicLink()) throw new Error('refusing to install a symbolic-link bundle')
  const pending = [root]
  while (pending.length > 0) {
    const directory = pending.pop()
    for (const item of await readdir(directory, { withFileTypes: true })) {
      const path = join(directory, item.name)
      if (item.isSymbolicLink()) {
        throw new Error('refusing to install a bundle containing symbolic links')
      }
      if (item.isDirectory()) pending.push(path)
    }
  }
}

async function rejectExistingSymlinks(root, target) {
  let current = root
  for (const segment of relative(root, target).split(sep)) {
    current = join(current, segment)
    try {
      const info = await lstat(current)
      if (info.isSymbolicLink()) {
        throw new Error(`refusing to install through symbolic-link directory: ${current}`)
      }
    } catch (error) {
      if (error.code === 'ENOENT') return
      throw error
    }
  }
}

async function copyBundle(source, destination) {
  for (const item of await readdir(source)) {
    await cp(join(source, item), join(destination, item), {
      recursive: true,
      errorOnExist: true,
      force: false,
      verbatimSymlinks: false,
    })
  }
}

async function readLock(path) {
  try {
    const value = JSON.parse(await readFile(path, 'utf8'))
    if (value?.schema_version !== 1 || value.skills === null || typeof value.skills !== 'object' || Array.isArray(value.skills)) {
      throw new Error(`invalid lock file: ${path}`)
    }
    return value
  } catch (error) {
    if (error.code === 'ENOENT') return { schema_version: 1, skills: {} }
    if (error instanceof SyntaxError) throw new Error(`invalid lock file: ${path}`)
    throw error
  }
}

async function writeLock(path, value) {
  const temporary = `${path}.${process.pid}.${Date.now()}.tmp`
  try {
    await writeFile(temporary, `${JSON.stringify(value, null, 2)}\n`, { encoding: 'utf8', flag: 'wx' })
    await rename(temporary, path)
  } finally {
    await rm(temporary, { force: true })
  }
}

async function pathExists(path) {
  try {
    await lstat(path)
    return true
  } catch (error) {
    if (error.code === 'ENOENT') return false
    throw error
  }
}

function assertWithin(parent, child, label) {
  const relation = relative(parent, child)
  if (relation === '' || (!relation.startsWith(`..${sep}`) && relation !== '..' && !isAbsolute(relation))) return
  throw new Error(`${label} escapes its parent directory`)
}

function throwIfAborted(signal) {
  if (signal?.aborted) throw abortError()
}

function abortError() {
  const error = new Error('skill installation was aborted')
  error.name = 'AbortError'
  return error
}

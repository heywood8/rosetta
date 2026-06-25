#!/usr/bin/env node
// Rosetta hooks diagnostics — a dump-first tester usable with ANY hook.
// Reads stdin, then IMMEDIATELY (before parsing) appends a full dump — argv, cwd, raw stdin,
// every env var — to ~/.rosetta/hooks.log, one `[<ISO-ms-timestamp>] [<pid>] <message>` line each.
// Then it JSON-parses the input and runs flag-selected processors. Each `--flag` maps to ONE
// processor fn(input, argValue, output) that mutates `output` ({ text, exitCode }); the runner
// writes output.text to stdout and exits with output.exitCode. Add copilot/codex-specific
// handling later by adding a processor function + a PROCESSORS entry — nothing else changes.
// Usage: <hook stdin> | node tester.js [--exit-code <n>] [--output <text>]
// (!) The env dump WILL capture secrets/tokens present in the hook environment. The log lives at
//     ~/.rosetta/hooks.log (outside any repo) — do not share or commit it.

'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');

const LOG_DIR = path.join(os.homedir(), '.rosetta');
const LOG_FILE = path.join(LOG_DIR, 'hooks.log');

// Append `message` to the log; every physical line is prefixed `[<ms-timestamp>] [<pid>] `.
// Never throws — diagnostics must not break the host hook.
function log(message) {
  const prefix = `[${new Date().toISOString()}] [${process.pid}] `;
  const body = String(message).split('\n').map((line) => prefix + line).join('\n');
  try {
    fs.mkdirSync(LOG_DIR, { recursive: true });
    fs.appendFileSync(LOG_FILE, body + '\n');
  } catch (_) {
    /* swallow: a failed log must never abort the hook */
  }
}

// Read all of stdin synchronously (fd 0). Returns '' if stdin is absent or unreadable.
function readStdin() {
  try {
    return fs.readFileSync(0, 'utf8');
  } catch (_) {
    return '';
  }
}

// Minimal flag parser. Supports `--flag value` and `--flag=value`; a flag with no value -> true.
function parseFlags(argv) {
  const flags = {};
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (!arg.startsWith('--')) continue;
    const eq = arg.indexOf('=');
    if (eq !== -1) {
      flags[arg.slice(0, eq)] = arg.slice(eq + 1);
    } else {
      const next = argv[i + 1];
      if (next !== undefined && !next.startsWith('--')) {
        flags[arg] = next;
        i++;
      } else {
        flags[arg] = true;
      }
    }
  }
  return flags;
}

// Processors: (input, argValue, output) => void. Each mutates `output`. Keyed by flag.
const PROCESSORS = {
  // Set the process exit code to the provided value.
  '--exit-code': (input, value, output) => {
    const n = Number(value);
    if (Number.isFinite(n)) output.exitCode = n;
  },
  // Write the provided text to stdout (the hook return channel).
  '--output': (input, value, output) => {
    output.text = typeof value === 'string' ? value : '';
  },
};

function main() {
  const raw = readStdin();
  const argv = process.argv.slice(2);

  // 1) DUMP FIRST — before any parsing, so a malformed payload is still fully captured.
  log('===== hook invocation =====');
  log('ARGV: ' + JSON.stringify(argv));
  log('CWD: ' + process.cwd());
  log('RAW STDIN:');
  log(raw.length ? raw : '<empty>');
  log('ENV:');
  for (const key of Object.keys(process.env).sort()) {
    log(`  ${key}=${process.env[key]}`);
  }

  // 2) Parse input (best-effort) and record the outcome.
  let input = null;
  if (raw.trim().length) {
    try {
      input = JSON.parse(raw);
      log('PARSED INPUT: ' + JSON.stringify(input));
    } catch (e) {
      log('PARSE ERROR: ' + e.message);
    }
  } else {
    log('PARSED INPUT: <no stdin>');
  }

  // 3) Run flag-selected processors over a mutable output accumulator.
  const flags = parseFlags(argv);
  const output = { text: '', exitCode: 0 };
  for (const flag of Object.keys(flags)) {
    const proc = PROCESSORS[flag];
    if (!proc) {
      log('UNKNOWN FLAG (ignored): ' + flag);
      continue;
    }
    log(`PROCESSOR: ${flag} (value=${JSON.stringify(flags[flag])})`);
    proc(input, flags[flag], output);
  }

  // 4) Emit: provided text -> stdout, then exit with the resolved code.
  if (output.text) process.stdout.write(output.text);
  log(`RESULT: exitCode=${output.exitCode} textLen=${output.text.length}`);
  log('');
  process.exit(output.exitCode);
}

main();

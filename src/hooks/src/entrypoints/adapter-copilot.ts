// Slim adapter for core-copilot bundle — copilot-only, zero other IDE code.
// The copilot adapter itself handles both Copilot CLI's camelCase fire (toolName/toolArgs)
// and the snake_case fire shared by VS Code + Copilot CLI's PascalCase fire (hook_event_name/
// tool_name/tool_input) — see docs/hooks/copilot.md and adapters/copilot.ts.
import { copilot } from '../adapters/copilot';
import type { NormalizedInput, CanonicalOutput } from '../types';

export const readStdin = (stream: NodeJS.ReadableStream = process.stdin): Promise<unknown> =>
  new Promise((resolve, reject) => {
    const chunks: string[] = [];
    stream.on('data', (chunk: unknown) => chunks.push(String(chunk)));
    stream.on('end', () => {
      const raw = chunks.join('').trim();
      if (!raw) return reject(new Error('Invalid input: empty stdin'));
      try { resolve(JSON.parse(raw)); }
      catch (err) { reject(new Error(`JSON parse error: ${(err as Error).message}`)); }
    });
    stream.on('error', reject);
  });

export const normalize = (rawInput: unknown): NormalizedInput =>
  copilot.normalize(rawInput as Record<string, unknown>);

export const formatOutput = (
  canonical: CanonicalOutput | Record<string, unknown>,
  _ide?: string,
): Record<string, unknown> => copilot.formatOutput(canonical as CanonicalOutput);

export const detectIDE = (_raw: unknown): string => 'copilot';

// Copilot deny is carried entirely in the JSON body at exit 0 — no adapter override needed.
export const exitCodeFor = (_canonical: CanonicalOutput, _ide?: string): number => 0;

export const stderrMessageFor = (_canonical: CanonicalOutput, _ide?: string): string | undefined => undefined;

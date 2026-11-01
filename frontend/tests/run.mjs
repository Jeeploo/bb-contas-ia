import process from 'node:process';
import { build } from 'esbuild';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
const directory = await mkdtemp(join(tmpdir(), 'bb-frontend-tests-'));
try {
  const outfile = join(directory, 'tests.cjs');
  await build({ entryPoints: ['tests/competencia.test.tsx'], outfile, bundle: true, platform:'node', format:'cjs', jsx:'automatic', define:{'import.meta.env.VITE_API_URL':'"https://api.test.invalid"' } });
  const result = spawnSync(process.execPath, [outfile], { stdio:'inherit' });
  process.exitCode = result.status ?? 1;
} finally { await rm(directory, { recursive:true, force:true }); }

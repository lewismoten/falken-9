import {createLauncher} from './launcher.mjs';
const status = message => {document.querySelector('#status').textContent = message;};
const controller = new AbortController();
const inventoryTimer = window.setTimeout(() => controller.abort(), 10000);
const retry = document.querySelector('#retry');
retry.addEventListener('click', () => window.location.reload());
try {
  const response = await fetch('release.json', {cache: 'no-store', signal: controller.signal});
  if (!response.ok) throw new Error(`Release inventory HTTP ${response.status}`);
  const manifest = await response.json();
  const launcher = createLauncher({window, manifest, fetch: window.fetch.bind(window), status});
  for (const format of ['prg', 'd64']) {
    if (!/^downloads\/[A-Za-z0-9._-]+\.(prg|d64)$/.test(manifest[format].path)) throw new Error('Unsafe download path.');
    const link = document.querySelector(`#${format}`);
    link.href = manifest[format].path;
    link.download = manifest[format].path.split('/').at(-1);
  }
  const run = document.querySelector('#run');
  const inspect = document.querySelector('#inspect');
  run.disabled = false;inspect.disabled = false;
  run.addEventListener('click', () => {
    run.disabled = true;
    launcher.run().finally(() => {run.disabled = false;});
  });
  inspect.addEventListener('click', () => {
    inspect.disabled = true;
    launcher.inspect().finally(() => {inspect.disabled = false;});
  });
  status(`Release ${manifest.release_id}. Every transmitted file is checked against its size and SHA-256.`);
} catch (error) {
  status(`Launcher unavailable: ${controller.signal.aborted ? 'Release inventory timed out.' : error.message} Reload to retry.`);
  retry.hidden = false;
} finally {window.clearTimeout(inventoryTimer);}

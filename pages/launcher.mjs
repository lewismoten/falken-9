// Minimal adaptation of Lewis Moten's sector-256/pages/index.js transports.
// Protocol attribution: docs/PAGES.md. No emulator or D64 parser is embedded.
export const TY64_URL = 'https://ty64.krissz.hu/';
export const INSPECTOR_URL = 'https://lewismoten.github.io/storage-d64/';

export function createLauncher({window: win, manifest, fetch: fetchBytes, status = () => {}}) {
  let inspecting = false;
  let ownedInspector = null;
  const ownershipKey = 'falken9-inspector-opened';
  function survivingInspector() {
    try {return win.sessionStorage?.getItem(ownershipKey) === '1';}
    catch {return false;} // Storage-disabled browsers retain the manual retry.
  }
  async function binary(record) {
    if (!/^downloads\/[A-Za-z0-9._-]+\.(prg|d64)$/.test(record.path)) throw new Error('Unsafe artifact path.');
    const url = new URL(record.path, win.location.href);
    if (url.origin !== new URL(win.location.href).origin) throw new Error('Artifact must be same-origin.');
    const controller = new AbortController();
    const timer = win.setTimeout(() => controller.abort(), 10000);
    try {
      const response = await fetchBytes(record.path, {signal: controller.signal, cache: 'no-store'});
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const bytes = new Uint8Array(await response.arrayBuffer());
      const digest = Array.from(new Uint8Array(await win.crypto.subtle.digest('SHA-256', bytes)), b => b.toString(16).padStart(2, '0')).join('');
      if (bytes.length !== record.bytes || digest !== record.sha256) throw new Error('Artifact size/SHA-256 mismatch.');
      return bytes;
    } finally {win.clearTimeout(timer);}
  }
  function fail(error) {status(`${error.message} Retry or download the file and load it manually.`);return false;}
  // Must remain synchronous through window.open: do not fetch first.
  async function run() {
    let tab;
    try {tab = win.open(TY64_URL, 'ty64');}
    catch (error) {return fail(error);}
    if (!tab) return fail(new Error('Popup blocked. Allow popups for this page.'));
    status('Fetching verified PRG…');
    try {
      const bytes = await binary(manifest.prg);
      await new Promise(resolve => win.setTimeout(resolve, 3000));
      if (tab.closed) throw new Error('Emulator window closed.');
      tab.postMessage(bytes, new URL(TY64_URL).origin);
      status('PRG posted to TY64. Switch to that tab. No readiness acknowledgment is available; retry if it was not ready.');
      return true;
    } catch (error) {return fail(error);}
  }
  async function inspect() {
    if (inspecting) return false;
    inspecting = true;
    const requestId = win.crypto.randomUUID();
    const origin = new URL(INSPECTOR_URL).origin;
    let tab, timer, onMessage;
    const cleanup = () => {win.clearTimeout(timer);if (onMessage) win.removeEventListener('message', onMessage);};
    try {
      // The receiver announces ready only on document load, not hashchange.
      // A repeated named-window #receive navigation alone cannot handshake.
      if (ownedInspector && !ownedInspector.closed) ownedInspector.close();
      status('Opening disk inspector…');
      await new Promise((resolve, reject) => {
        onMessage = event => {
          if (event.source !== tab || event.origin !== origin) return;
          if (event.data?.type !== 'storage-d64:ready' || event.data.receiveRequestId !== requestId) return;
          cleanup();resolve();
        };
        win.addEventListener('message', onMessage);
        timer = win.setTimeout(() => {cleanup();reject(new Error('Disk inspector readiness timed out.'));}, 10000);
        if (!ownedInspector && survivingInspector()) {
          // Recover only our popup after a launcher reload. An empty-URL open
          // obtains the named window without navigating its current document.
          const previous = win.open('', 'storage-d64-inspector');
          if (!previous) throw new Error('Popup blocked. Allow popups for this page.');
          let blank = false;
          try {blank = previous.location.href === 'about:blank';} catch { /* cross-origin inspector */ }
          if (!blank) {
            if (previous.opener !== win) throw new Error('The existing inspector belongs to another page. Close that window before retrying.');
            previous.close();
          }
        }
        tab = win.open(`${INSPECTOR_URL}#receive=${encodeURIComponent(requestId)}`, 'storage-d64-inspector');
        ownedInspector = tab;
        if (!tab) {cleanup();reject(new Error('Popup blocked. Allow popups for this page.'));}
        else {try {win.sessionStorage?.setItem(ownershipKey, '1');} catch { /* optional ownership recovery */ }}
      });
      const bytes = await binary(manifest.d64);
      if (tab.closed) throw new Error('Disk inspector window closed.');
      const sourceName = manifest.d64.path.split('/').at(-1);
      tab.postMessage({type: 'storage-d64:load', sourceName, bytes}, origin);
      status(`${sourceName} posted. Switch to the inspector tab to examine the directory.`);
      return true;
    } catch (error) {return fail(error);}
    finally {cleanup();inspecting = false;}
  }
  return {run, inspect};
}

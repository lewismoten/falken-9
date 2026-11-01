import test from 'node:test';
import assert from 'node:assert/strict';
import {existsSync} from 'node:fs';

test('launcher implements owner-authorized binary window transports', async () => {
  assert.ok(existsSync(new URL('../pages/launcher.mjs', import.meta.url)), 'missing launcher transport');
  const {createLauncher, TY64_URL, INSPECTOR_URL}=await import('../pages/launcher.mjs');
  const listeners=new Set(), timers=new Map(), posts=[];let next=0, opened;
  const win={location:{href:'http://127.0.0.1:8847/sub/'},crypto,
    open(url,name){opened={url,name,closed:false,postMessage:(...args)=>posts.push(args)};return opened;},
    addEventListener(type,fn){listeners.add(fn)},removeEventListener(type,fn){listeners.delete(fn)},
    setTimeout(fn,ms){const id=++next;timers.set(id,{fn:()=>{timers.delete(id);fn()},ms});return id},clearTimeout(id){timers.delete(id)}};
  const raw=new Uint8Array([1,8,12,8,10,0,158]);
  const sha=Buffer.from(await crypto.subtle.digest('SHA-256',raw)).toString('hex');
  const manifest={prg:{path:'downloads/game.prg',bytes:raw.length,sha256:sha},d64:{path:'downloads/game.d64',bytes:raw.length,sha256:sha}};
  const fetches=[];
  const launcher=createLauncher({window:win,manifest,fetch:async(path)=>{fetches.push(path);return {ok:true,arrayBuffer:async()=>raw.buffer}}});
  const run=launcher.run();assert.equal(opened.url,TY64_URL,'popup must open before async fetch');
  for(let i=0;i<100 && ![...timers.values()].some(t=>t.ms===3000);i++) await new Promise(r=>setTimeout(r,1));
  [...timers.values()].find(t=>t.ms===3000).fn();await run;
  assert.ok(posts[0][0] instanceof Uint8Array);assert.deepEqual(posts[0][0],raw);
  assert.equal(posts[0][1],new URL(TY64_URL).origin);
  posts.length=0;
  const inspect=launcher.inspect();assert.equal(listeners.size,1);
  const requestId=decodeURIComponent(new URL(opened.url).hash.slice('#receive='.length));
  const origin=new URL(INSPECTOR_URL).origin;
  const emit=(patch={})=>{for(const fn of listeners)fn({source:opened,origin,data:{type:'storage-d64:ready',receiveRequestId:requestId},...patch})};
  emit({source:{}});emit({origin:'https://wrong.invalid'});emit({data:{type:'other',receiveRequestId:requestId}});emit({data:{type:'storage-d64:ready',receiveRequestId:'wrong'}});
  assert.equal(posts.length,0);assert.equal(listeners.size,1);
  emit();await inspect;
  assert.equal(listeners.size,0);assert.equal(timers.size,0);
  assert.deepEqual(posts[0],[{type:'storage-d64:load',sourceName:'game.d64',bytes:raw},origin]);
  assert.ok(fetches.every(p=>p.startsWith('downloads/')));
});

test('popup exceptions are reported as recoverable failures', async()=>{
  const {createLauncher}=await import('../pages/launcher.mjs');
  const statuses=[];
  const launcher=createLauncher({window:{open(){throw new Error('Window access denied')}},manifest:{},fetch(){throw new Error('must not fetch')},status:s=>statuses.push(s)});
  assert.equal(await launcher.run(),false);
  assert.match(statuses.at(-1),/Retry or download/);
});

test('repeated inspector launch starts a fresh owned receiver, not a hash-only navigation',async()=>{
  const {createLauncher,INSPECTOR_URL}=await import('../pages/launcher.mjs');
  const listeners=new Set();let opened;
  const win={location:{href:'http://127.0.0.1:8847/'},crypto,setTimeout,clearTimeout,
    addEventListener(t,f){listeners.add(f)},removeEventListener(t,f){listeners.delete(f)},
    open(url){opened={url,closed:false,close(){this.closed=true},postMessage(){}};return opened}};
  const bytes=new Uint8Array([1,2,3]);const sha=Buffer.from(await crypto.subtle.digest('SHA-256',bytes)).toString('hex');
  const launcher=createLauncher({window:win,manifest:{d64:{path:'downloads/test.d64',bytes:3,sha256:sha}},fetch:async()=>({ok:true,arrayBuffer:async()=>bytes.buffer})});
  const ready=()=>{for(const f of listeners)f({source:opened,origin:new URL(INSPECTOR_URL).origin,data:{type:'storage-d64:ready',receiveRequestId:decodeURIComponent(new URL(opened.url).hash.slice(9))}})};
  const a=launcher.inspect();ready();assert.equal(await a,true);const first=opened;
  const b=launcher.inspect();assert.equal(first.closed,true);ready();assert.equal(await b,true);
});

test('launcher reload safely refreshes its surviving owned inspector',async()=>{
  const {createLauncher,INSPECTOR_URL}=await import('../pages/launcher.mjs');
  const listeners=new Set(),stored=new Map();let opened;
  const win={location:{href:'http://127.0.0.1:8847/'},crypto,setTimeout,clearTimeout,
    sessionStorage:{getItem:k=>stored.get(k),setItem:(k,v)=>stored.set(k,v)},
    addEventListener(t,f){listeners.add(f)},removeEventListener(t,f){listeners.delete(f)},
    open(url){if(!opened||opened.closed)opened={url:url||'about:blank',opener:win,closed:false,close(){this.closed=true},postMessage(){},get location(){if(this.url==='about:blank')return {href:this.url};throw new Error('cross-origin')}};if(url)opened.url=url;return opened}};
  const bytes=new Uint8Array([1,2,3]);const sha=Buffer.from(await crypto.subtle.digest('SHA-256',bytes)).toString('hex');
  const config={window:win,manifest:{d64:{path:'downloads/test.d64',bytes:3,sha256:sha}},fetch:async()=>({ok:true,arrayBuffer:async()=>bytes.buffer})};
  const ready=()=>{for(const f of listeners)f({source:opened,origin:new URL(INSPECTOR_URL).origin,data:{type:'storage-d64:ready',receiveRequestId:decodeURIComponent(new URL(opened.url).hash.slice(9))}})};
  const firstLauncher=createLauncher(config);const a=firstLauncher.inspect();ready();assert.equal(await a,true);const old=opened;
  const reloaded=createLauncher(config);const b=reloaded.inspect();assert.equal(old.closed,true);ready();assert.equal(await b,true);
});

test('inspector popup, timeout, fetch and integrity failures clean up and retry',async()=>{
  const {createLauncher,INSPECTOR_URL}=await import('../pages/launcher.mjs');
  for(const fault of ['popup','timeout','fetch','http','corrupt','unsafe','closed']){
    let active=fault,opened,next=0;const listeners=new Set(),timers=new Map(),posts=[],statuses=[];
    const win={location:{href:'http://127.0.0.1:8847/sub/'},crypto,
      setTimeout(fn,ms){const id=++next;timers.set(id,{fn:()=>{timers.delete(id);fn()},ms});return id},clearTimeout:id=>timers.delete(id),
      addEventListener(t,f){listeners.add(f)},removeEventListener(t,f){listeners.delete(f)},
      open(url){if(active==='popup')return null;opened={url,closed:active==='closed',close(){this.closed=true},postMessage:(...a)=>posts.push(a)};return opened}};
    const bytes=new Uint8Array([1,8,12]);const sha=Buffer.from(await crypto.subtle.digest('SHA-256',bytes)).toString('hex');
    const record={path:active==='unsafe'?'https://outside.invalid/game.d64':'downloads/test.d64',bytes:3,sha256:sha};
    const launcher=createLauncher({window:win,manifest:{d64:record},status:s=>statuses.push(s),fetch:async()=>{if(active==='fetch')throw new Error('network failed');return {ok:active!=='http',status:503,arrayBuffer:async()=>active==='corrupt'?new Uint8Array([0]).buffer:bytes.buffer}}});
    const ready=()=>{for(const f of listeners)f({source:opened,origin:new URL(INSPECTOR_URL).origin,data:{type:'storage-d64:ready',receiveRequestId:decodeURIComponent(new URL(opened.url).hash.slice(9))}})};
    let operation=launcher.inspect();
    if(fault==='timeout')[...timers.values()].find(t=>t.ms===10000).fn();else if(fault!=='popup')ready();
    assert.equal(await operation,false,fault);assert.equal(listeners.size,0,fault);assert.equal(timers.size,0,fault);assert.equal(posts.length,0,fault);assert.match(statuses.at(-1),/Retry or download/);
    active=null;record.path='downloads/test.d64';operation=launcher.inspect();ready();assert.equal(await operation,true,fault);assert.equal(posts.length,1);assert.equal(listeners.size,0);assert.equal(timers.size,0);
  }
});

test('inventory timeout cleans its timer and exposes reload recovery',async()=>{
  const previous={window:globalThis.window,document:globalThis.document,fetch:globalThis.fetch};
  const nodes=new Map(),timers=new Map();let reloaded=false;
  const node=id=>{if(!nodes.has(id))nodes.set(id,{hidden:true,disabled:true,addEventListener(t,f){this[t]=f}});return nodes.get(id)};
  try {
    globalThis.document={querySelector:node};
    globalThis.fetch=async(path,{signal}={})=>new Promise((resolve,reject)=>signal?.addEventListener('abort',()=>reject(new Error('aborted')),{once:true}));
    globalThis.window={fetch:globalThis.fetch,location:{reload(){reloaded=true}},setTimeout(f,ms){timers.set(1,{f,ms});return 1},clearTimeout:id=>timers.delete(id)};
    const loaded=import('../pages/index.mjs?inventory-timeout');
    for(let i=0;i<20&&!timers.size;i++)await new Promise(resolve=>setTimeout(resolve,1));
    assert.equal(timers.get(1)?.ms,10000);timers.get(1).f();await loaded;
    assert.equal(timers.size,0);assert.equal(node('#retry').hidden,false);assert.equal(node('#run').disabled,true);assert.match(node('#status').textContent,/timed out/);
    node('#retry').click();assert.equal(reloaded,true);
  } finally {Object.assign(globalThis,previous);}
});

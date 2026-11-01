// Access is obtained by the agent from Sites, never saved in the project.
// Input on stdin: {serviceToken}. The destination comes only from the registered
// Site identity saved from native Sites responses, never from task input.
import {readFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {resolve} from 'node:path';
const root = fileURLToPath(new URL('..',import.meta.url));
let input=''; for await (const chunk of process.stdin) input+=chunk;
try {
  const {serviceToken}=JSON.parse(input);
  const manifest=JSON.parse(await readFile(new URL('../.openai/hosting.json',import.meta.url),'utf8'));
  const registration=JSON.parse(await readFile(new URL('../sites/registered-site.json',import.meta.url),'utf8'));
  if(!manifest.project_id || manifest.project_id!==registration.projectId)throw Error('Registered Site identity required');
  const base=new URL(registration.origin);
  if (base.protocol!=='https:' || base.username || base.password || base.pathname!=='/' || base.search || base.hash || !serviceToken) throw Error('HTTPS Site origin and service access required');
  const validation=spawnSync('python',['-B','scripts/check_sites_news.py'],{cwd:root,encoding:'utf8',env:{...process.env,PYTHONPYCACHEPREFIX:resolve(root,'tmp/pycache'),PYTHONIOENCODING:'utf-8'}});
  if(validation.status!==0)throw Error('Local Python news validation failed; nothing uploaded');
  const headers={'OAI-Sites-Authorization':'Bearer '+serviceToken};
  const response=await fetch(new URL('/api/state',base),{headers,redirect:'error'});
  if(!response.ok)throw Error('Site read failed: '+response.status);
  const state=await response.json();
  const news=JSON.parse(await readFile(new URL('../data/news.json',import.meta.url),'utf8'));
  const write=await fetch(new URL('/api/news',base),{method:'PUT',headers:{...headers,'Content-Type':'application/json'},body:JSON.stringify({revision:state.revision,news}),redirect:'error'});
  if(!write.ok)throw Error('News write failed: '+write.status);
  const readback=await fetch(new URL('/data/news.json',base),{headers,redirect:'error'});
  if(!readback.ok || JSON.stringify(await readback.json())!==JSON.stringify(news))throw Error('News readback mismatch');
  console.log(JSON.stringify({updated:true,generatedAt:news.generatedAt}));
} catch {
  // Parser and HTTP errors can contain input/header values. Never echo them.
  console.error('Sites update failed. Check registration, Python validation, service access and readback.');
  process.exitCode=1;
}

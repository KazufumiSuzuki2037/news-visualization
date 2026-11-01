import {createServer} from 'node:http';
import {readFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {resolve} from 'node:path';
import {FileBucket} from '../sites/local-bucket.mjs';
const root = fileURLToPath(new URL('..',import.meta.url));
const source = await readFile(resolve(root,'dist/server/index.js'),'utf8');
const {default:app} = await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const env = {BUCKET:new FileBucket(resolve(root,'tmp/sites-preview'))};
const port = 8768;
createServer(async (incoming,outgoing) => {
  if (!['127.0.0.1:'+port,'localhost:'+port].includes(incoming.headers.host)) {outgoing.writeHead(403);outgoing.end();return;}
  try {
    const headers = {...incoming.headers,'oai-authenticated-user-id':'preview-owner'};
    const body = ['GET','HEAD'].includes(incoming.method) ? undefined : incoming;
    const response = await app.fetch(new Request('http://'+incoming.headers.host+incoming.url,{method:incoming.method,headers,body,duplex:'half'}),env);
    outgoing.writeHead(response.status,Object.fromEntries(response.headers));outgoing.end(Buffer.from(await response.arrayBuffer()));
  } catch {outgoing.writeHead(500);outgoing.end('Preview request failed');}
}).listen(port,'127.0.0.1',()=>console.log('Sites local preview: http://127.0.0.1:'+port+'/'));

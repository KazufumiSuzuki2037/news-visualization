import {readFile,writeFile,mkdir,readdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {resolve,join,extname} from 'node:path';
const root = fileURLToPath(new URL('..',import.meta.url));
const read = async path => JSON.parse(await readFile(join(root,path),'utf8'));
const initial = {settings:await read('config/settings.json'),news:await read('data/news.json'),display:await read('config/display.json'),scoring:await read('config/scoring.json'),researchStatus:null,assets:{}};
try {initial.researchStatus = await read('data/research-status.json');} catch (error) {if (error.code !== 'ENOENT') throw error;}
async function assets(directory) {
  for (const entry of await readdir(join(root,'web',directory),{withFileTypes:true})) {
    const path = join(directory,entry.name);
    if (entry.isDirectory()) await assets(path);
    else if (entry.isFile()) {
      const type = {'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.txt':'text/plain; charset=utf-8'}[extname(path)];
      if (!type) throw Error('Unsupported asset: '+path);
      initial.assets['/'+path.replaceAll('\\','/')] = {type,body:await readFile(join(root,'web',path),'utf8')};
    } else throw Error('Nonregular asset: '+path);
  }
}
await assets(''); initial.assets['/'] = initial.assets['/index.html'];
const source = await readFile(join(root,'sites/worker.mjs'),'utf8');
const output = resolve(root,'dist/server'); await mkdir(output,{recursive:true});
await mkdir(resolve(root,'dist/.openai'),{recursive:true});
await writeFile(join(output,'index.js'),source+'\nexport default createApp('+JSON.stringify(initial)+');\n','utf8');
await writeFile(resolve(root,'dist/.openai/hosting.json'),JSON.stringify(await read('.openai/hosting.json'),null,2)+'\n','utf8');
console.log('Sites Worker built without dependency installation: dist/server/index.js');

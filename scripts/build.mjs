import {pathToFileURL} from 'node:url';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {copyFile} from 'node:fs/promises';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
// Use this project's locked dependencies. Run npm ci explicitly before building.
const modules=path.join(root,'node_modules');
const {build}=await import(pathToFileURL(path.join(modules,'vite/dist/node/index.js')).href);
await build({root:path.join(root,'frontend'),configFile:false,publicDir:false,
 resolve:{alias:[{find:/^react$/,replacement:path.join(modules,'react/index.js')},{find:/^react\/jsx-runtime$/,replacement:path.join(modules,'react/jsx-runtime.js')},{find:/^react-dom\/client$/,replacement:path.join(modules,'react-dom/client.js')},{find:/^react-dom$/,replacement:path.join(modules,'react-dom/index.js')}]},
 define:{'process.env.NODE_ENV':JSON.stringify('production')},
 oxc:{jsx:{runtime:'automatic'}},build:{outDir:path.join(root,'web'),emptyOutDir:true,sourcemap:false}});
await copyFile(path.join(root,'LICENSE'),path.join(root,'web/LICENSE.txt'));
await copyFile(path.join(root,'THIRD_PARTY_NOTICES.txt'),path.join(root,'web/THIRD_PARTY_NOTICES.txt'));

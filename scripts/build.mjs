import {pathToFileURL} from 'node:url';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
// Supply an existing node_modules directory. This script never installs packages.
const modules=process.env.NV_NODE_MODULES;
if(!modules)throw Error('Set NV_NODE_MODULES to an existing node_modules directory containing vite, react, and react-dom.');
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const {build}=await import(pathToFileURL(path.join(modules,'vite/dist/node/index.js')).href);
await build({root:path.join(root,'frontend'),configFile:false,publicDir:false,
 resolve:{alias:[{find:/^react$/,replacement:path.join(modules,'react/index.js')},{find:/^react\/jsx-runtime$/,replacement:path.join(modules,'react/jsx-runtime.js')},{find:/^react-dom\/client$/,replacement:path.join(modules,'react-dom/client.js')},{find:/^react-dom$/,replacement:path.join(modules,'react-dom/index.js')}]},
 define:{'process.env.NODE_ENV':JSON.stringify('production')},
 oxc:{jsx:{runtime:'automatic'}},build:{outDir:path.join(root,'web'),emptyOutDir:true,sourcemap:false}});

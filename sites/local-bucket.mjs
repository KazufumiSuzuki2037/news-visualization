// Filesystem implementation for preview/tests only. Hosted code uses native R2.
import {readFile,writeFile,mkdir,rename} from 'node:fs/promises';
import {resolve} from 'node:path';
import {createHash,randomUUID} from 'node:crypto';
export class FileBucket {
  constructor(directory) {this.directory=directory;this.pending=Promise.resolve();}
  path(key) {return resolve(this.directory,Buffer.from(key).toString('base64url')+'.json');}
  async get(key) {
    try {const text=await readFile(this.path(key),'utf8');return {etag:createHash('sha256').update(text).digest('hex'),json:async()=>JSON.parse(text)};}
    catch(error) {if(error.code==='ENOENT')return null;throw error;}
  }
  put(key,text,options={}) {
    const operation=this.pending.then(async()=>{
      const current=await this.get(key),condition=options.onlyIf;
      if(condition && (condition.etagMatches && condition.etagMatches!==current?.etag || condition.etagDoesNotMatch==='*' && current))return null;
      await mkdir(this.directory,{recursive:true});const path=this.path(key),temporary=path+'.'+randomUUID()+'.tmp';
      await writeFile(temporary,text,'utf8');await rename(temporary,path);return {etag:createHash('sha256').update(text).digest('hex')};
    });this.pending=operation.catch(()=>{});return operation;
  }
}

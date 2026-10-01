import {createServer} from 'node:http';
import {readFile,mkdir} from 'node:fs/promises';
import {randomBytes} from 'node:crypto';
import {localDatabase} from './local-db.mjs';
import {handleApi} from '../server/api.js';
await mkdir(new URL('../.local/',import.meta.url),{recursive:true});
const DB=localDatabase(new URL('../.local/leaderboard.sqlite',import.meta.url).pathname),token=randomBytes(24).toString('hex');
const files={'/':['index.html','text/html'],'/index.html':['index.html','text/html'],'/style.css':['style.css','text/css'],'/app.js':['app.js','text/javascript'],'/ranked.js':['ranked.js','text/javascript']};
createServer(async(req,res)=>{
 try{
  const base='http://127.0.0.1:4173',url=new URL(req.url,base);
  if(url.pathname==='/signin-with-chatgpt'){res.writeHead(302,{'Set-Cookie':`pocket_preview=${token}; HttpOnly; SameSite=Lax; Path=/`,'Location':'/'});return res.end();}
  if(url.pathname==='/signout-with-chatgpt'){res.writeHead(302,{'Set-Cookie':'pocket_preview=; Max-Age=0; Path=/','Location':'/'});return res.end();}
  if(url.pathname.startsWith('/api/')){
   const headers=new Headers();for(const [k,v] of Object.entries(req.headers))if(v&&!k.startsWith('oai-'))headers.set(k,Array.isArray(v)?v.join(','):v);
   if((req.headers.cookie||'').split(';').some(c=>c.trim()===`pocket_preview=${token}`)){headers.set('oai-authenticated-user-id','local-preview-player');headers.set('oai-authenticated-user-email','preview@sites.test');}
   const chunks=[];let bytes=0;for await(const c of req){bytes+=c.length;if(bytes>4096){res.writeHead(413);res.end();return;}chunks.push(c);}
   const response=await handleApi(new Request(url,{method:req.method,headers,...(chunks.length?{body:Buffer.concat(chunks)}:{})}),{DB,LOCAL_PREVIEW:true});
   res.writeHead(response.status,Object.fromEntries(response.headers));return res.end(Buffer.from(await response.arrayBuffer()));
  }
  const asset=files[url.pathname];if(!asset){res.writeHead(404);return res.end('Not found');}
  const data=await readFile(new URL('../client/'+asset[0],import.meta.url));res.writeHead(200,{'Content-Type':asset[1]+'; charset=utf-8','Cache-Control':'no-store'});res.end(data);
 }catch(e){console.error(e);res.writeHead(500);res.end('Preview unavailable');}
}).listen(4173,'127.0.0.1',()=>console.log('Pocket Puzzles: http://127.0.0.1:4173 — local test leaderboard'));

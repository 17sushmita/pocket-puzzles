import {handleApi} from './api.js';
import html from '../client/index.html?raw';
import css from '../client/style.css?raw';
import js from '../client/app.js?raw';
import ranked from '../client/ranked.js?raw';
const assets={'/':[html,'text/html'],'/index.html':[html,'text/html'],'/style.css':[css,'text/css'],'/app.js':[js,'text/javascript'],'/ranked.js':[ranked,'text/javascript']};
export default {async fetch(req,env){const path=new URL(req.url).pathname;if(path.startsWith('/api/'))return handleApi(req,env);const asset=assets[path];if(!asset)return new Response('Not found',{status:404});return new Response(req.method==='HEAD'?null:asset[0],{headers:{'Content-Type':asset[1]+'; charset=utf-8','Cache-Control':'no-cache','X-Content-Type-Options':'nosniff','Referrer-Policy':'same-origin'}});}};

import {database} from './db.js';
import {games,difficulties,generate,advance,visibleState,dayKey,nextReset} from './game.js';
const json=(data,status=200)=>Response.json(data,{status,headers:{'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
class HttpError extends Error{constructor(message,status=400){super(message);this.status=status;}}
const requireValue=(condition,message,status=400)=>{if(!condition)throw new HttpError(message,status);};
function identity(req){const id=req.headers.get('oai-authenticated-user-id'),email=req.headers.get('oai-authenticated-user-email');return id&&email?id:null;}
function options(url){const game=url.searchParams.get('game'),difficulty=url.searchParams.get('difficulty');requireValue(games.includes(game)&&difficulties.includes(difficulty),'Choose a valid game and difficulty.');return {game,difficulty};}
async function body(req){requireValue((req.headers.get('content-type')||'').startsWith('application/json'),'Send JSON.');const text=await req.text();requireValue(text.length<=4096,'Request is too large.',413);try{return JSON.parse(text);}catch{throw new HttpError('Invalid JSON.');}}
function publicAttempt(row,now){if(!row)return null;return {id:row.id,revision:row.revision,startedAt:row.started_at,finishedAt:row.finished_at,elapsedMs:row.elapsed_ms,state:visibleState(JSON.parse(row.state),now)};}
async function challenge(db,game,difficulty,now){const day=dayKey(now),id=day+':'+game+':'+difficulty;let found=await db.first('SELECT * FROM challenges WHERE id = ?',id);if(!found){await db.run('INSERT OR IGNORE INTO challenges (id,day,game,difficulty,puzzle,created_at) VALUES (?,?,?,?,?,?)',id,day,game,difficulty,JSON.stringify(generate(game,difficulty)),now);found=await db.first('SELECT * FROM challenges WHERE id = ?',id);}return found;}
async function rankings(db,c,id){
 const ranked=`SELECT a.player_id, p.display_name, a.moves, a.elapsed_ms, a.finished_at, RANK() OVER (ORDER BY a.moves,a.elapsed_ms) AS rank FROM attempts a JOIN players p ON p.id=a.player_id WHERE a.challenge_id=? AND a.finished_at IS NOT NULL`;
 const rows=await db.all('SELECT * FROM ('+ranked+') ORDER BY rank,finished_at,player_id LIMIT 50',c.id);
 const mine=await db.first('SELECT * FROM ('+ranked+') WHERE player_id=?',c.id,id);
 const count=await db.first('SELECT COUNT(*) AS count FROM attempts WHERE challenge_id=? AND finished_at IS NOT NULL',c.id);
 const best=await db.first('SELECT MIN(a.moves) AS moves FROM attempts a JOIN challenges c ON c.id=a.challenge_id WHERE a.player_id=? AND c.game=? AND c.difficulty=? AND a.finished_at IS NOT NULL',id,c.game,c.difficulty);
 const clean=r=>r?{rank:r.rank,name:r.display_name,moves:r.moves,elapsedMs:r.elapsed_ms,isYou:r.player_id===id}:null;
 return {rows:rows.map(clean),mine:clean(mine),count:count.count,personalBest:best.moves,gap:mine&&rows[0]?mine.moves-rows[0].moves:null};
}
export async function handleApi(req,env,now=Date.now()){
 try{
  const url=new URL(req.url),path=url.pathname,id=identity(req);
  if(path==='/api/session'&&req.method==='GET'){
   if(!id)return json({user:null,local:!!env.LOCAL_PREVIEW});
   const db=database(env);return json({user:{profile:await db.first('SELECT display_name FROM players WHERE id=?',id)},local:!!env.LOCAL_PREVIEW});
  }
  requireValue(id,'Sign in to play ranked challenges.',401);
  const db=database(env);
  if(req.method!=='GET')requireValue(req.headers.get('origin')===url.origin,'Request origin is not allowed.',403);
  if(path==='/api/profile'&&req.method==='PUT'){
   const input=await body(req),name=typeof input.name==='string'?input.name.trim().replace(/\s+/g,' '):'';
   requireValue(name.length>=2&&name.length<=24&&!/[\p{C}<>]/u.test(name),'Use 2–24 characters for your display name.');
   await db.run('INSERT INTO players (id,display_name,created_at) VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET display_name=excluded.display_name',id,name,now);return json({name});
  }
  if(path==='/api/daily'&&req.method==='GET'){
   const {game,difficulty}=options(url),c=await challenge(db,game,difficulty,now);
   const row=await db.first('SELECT * FROM attempts WHERE player_id=? AND challenge_id=?',id,c.id);
   return json({day:c.day,resetAt:nextReset(c.day),serverNow:now,attempt:publicAttempt(row,now),leaderboard:await rankings(db,c,id)});
  }
  if(path==='/api/start'&&req.method==='POST'){
   const {game,difficulty}=await body(req);requireValue(games.includes(game)&&difficulties.includes(difficulty),'Choose a valid game and difficulty.');
   requireValue(await db.first('SELECT id FROM players WHERE id=?',id),'Choose a display name first.',409);
   const c=await challenge(db,game,difficulty,now);
   await db.run('INSERT OR IGNORE INTO attempts (id,player_id,challenge_id,state,revision,started_at,moves) VALUES (?,?,?,?,0,?,0)',crypto.randomUUID(),id,c.id,c.puzzle,now);
   return json({attempt:publicAttempt(await db.first('SELECT * FROM attempts WHERE player_id=? AND challenge_id=?',id,c.id),now),serverNow:now});
  }
  if(path==='/api/move'&&req.method==='POST'){
   const input=await body(req);requireValue(typeof input.attemptId==='string'&&Number.isInteger(input.revision)&&input.revision>=0&&Number.isInteger(input.index),'Invalid move request.');
   const row=await db.first('SELECT a.*,c.day FROM attempts a JOIN challenges c ON c.id=a.challenge_id WHERE a.id=? AND a.player_id=?',input.attemptId,id);requireValue(row,'Attempt not found.',404);
   if(row.revision===input.revision+1&&row.last_index===input.index)return json({attempt:publicAttempt(row,now),serverNow:now});
   requireValue(row.day===dayKey(now),'This challenge has ended. Start today’s challenge.',410);
   requireValue(row.revision===input.revision,'Your attempt changed in another tab. Refresh to continue.',409);
   requireValue(row.revision<10000,'This attempt reached the move limit.',409);
   let next;try{next=advance(JSON.parse(row.state),input.index,now);}catch(e){throw new HttpError(e.message);}
   const result=await db.run('UPDATE attempts SET state=?,revision=revision+1,last_index=?,moves=?,finished_at=?,elapsed_ms=? WHERE id=? AND player_id=? AND revision=?',JSON.stringify(next),input.index,next.moves,next.won?now:null,next.won?Math.max(1,now-row.started_at):null,row.id,id,row.revision);
   requireValue(result.meta.changes===1,'Your attempt changed in another tab. Refresh to continue.',409);
   const updated=await db.first('SELECT * FROM attempts WHERE id=?',row.id);
   return json({attempt:publicAttempt(updated,now),serverNow:now});
  }
  return json({error:'Not found.'},404);
 }catch(e){if(!(e instanceof HttpError))console.error('Leaderboard request failed',e.message);return json({error:e instanceof HttpError?e.message:'The leaderboard is temporarily unavailable. Please try again.'},e.status||503);}
}

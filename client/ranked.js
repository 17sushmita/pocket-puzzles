(() => {
 let active=false,busy=false,attempt=null,session=null,data=null,sequence=0,offset=0,hideTimer=null,error='',loaded=false;
 let difficulty=$('difficulty').value;
 const field=document.querySelector('.playfield'),actions=document.querySelector('.actions');
 const duration=ms=>{const s=Math.floor(ms/1000);return `${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}`;};
 async function request(path,method='GET',input){const r=await fetch(path,{method,headers:input?{'Content-Type':'application/json'}:{},...(input?{body:JSON.stringify(input)}:{})});let body;try{body=await r.json();}catch{throw new Error('The leaderboard is unavailable. Try again in a moment.');}if(!r.ok)throw new Error(body.error||'Please try again.');return body;}
 function updateState(a){attempt=a;clearTimeout(hideTimer);if(a){state={...a.state,history:[],solution:[],round:1};if(state.flipped.length===2){hideTimer=setTimeout(()=>{if(active&&attempt?.id===a.id){state.flipped=[];state.board=state.board.map((v,i)=>state.matched.includes(i)?v:null);render();}},Math.max(0,state.hideAt-(Date.now()+offset))+30);}}else state=fresh(current,difficulty);focusHint=-1;render();}
 function header(){
  $('daily-panel').hidden=!active;$('leaderboard').hidden=!active;
  $('practice-mode').setAttribute('aria-pressed',String(!active));$('daily-mode').setAttribute('aria-pressed',String(active));
  if(!active){field.hidden=false;actions.hidden=false;return;}
  field.hidden=!attempt;actions.hidden=true;
  $('difficulty').value=difficulty;
  $('daily-date').textContent=data?new Intl.DateTimeFormat('en-IN',{day:'numeric',month:'short',timeZone:'Asia/Kolkata'}).format(new Date(data.day+'T12:00:00+05:30'))+' · Daily challenge':"Today's challenge";
  $('ranked-profile').hidden=!session?.user;
  $('ranked-signin').hidden=!loaded||!!session?.user;
  $('ranked-signin').textContent=session?.local?'Sign in to local preview':'Sign in with ChatGPT';
  $('ranked-start').hidden=!session?.user?.profile||!!attempt||!data;
  $('ranked-start').disabled=busy;$('ranked-refresh').disabled=busy;$('profile-form').querySelector('button').disabled=busy;
  let message=busy?'Saving your move…':!loaded?'Loading the leaderboard…':!session?.user?'Sign in to save your daily score and compete.':!session.user.profile?'Choose the name other players will see.':!attempt?'Same puzzle for everyone. Start when you’re ready.':attempt.state.won?'Your score is verified and saved. See how you placed below.':'Your first attempt is in progress. Every move is saved.';
  if(session?.local)message+=' Local preview scores are separate from the live leaderboard.';
  $('daily-message').textContent=error||message;
  $('daily-message').classList.toggle('error',!!error);
  if(attempt){$('round-label').textContent='DAILY · RANKED';$('save-note').textContent='Ranked progress saved on server';$('record').textContent=attempt.state.won?'Verified score':'One ranked attempt per day';const blocked=busy||state.won||!!(data&&Date.now()+offset>=data.resetAt);$('board').querySelectorAll('button').forEach((b,i)=>b.disabled=blocked||(current==='slide'&&state.board[i]===0)||(current==='memory'&&(state.matched.includes(i)||state.flipped.includes(i)||state.flipped.length===2)));$('palette').querySelectorAll('button').forEach((b,i)=>b.disabled=blocked||i===state.board[0]);}
  tick();
 }
 function tick(){if(!active)return;const now=Date.now()+offset;$('ranked-timer').textContent=attempt?duration(attempt.elapsedMs??Math.max(0,now-attempt.startedAt))+(attempt.finishedAt?' · Finished':' · Timer running'):'One ranked attempt';if(data&&now>=data.resetAt){$('ranked-timer').textContent='New challenge available';$('daily-message').textContent='Today’s challenge has ended. Refresh for the next one.';field.querySelectorAll('button').forEach(b=>b.disabled=true);}}
 function leaderboard(){const l=data?.leaderboard;$('leader-rows').replaceChildren();$('leader-unit').textContent=current==='memory'?'Turns':'Moves';$('leader-count').textContent=l?l.count+' finished':'';$('leader-empty').hidden=!!l?.rows.length;$('leader-empty').textContent=loaded&&session?.user?'Be the first to finish today’s puzzle.':'Sign in to see today’s scores.';$('leader-summary').textContent='';$('leader-best').textContent='';if(!l)return;
  for(const row of l.rows){const tr=document.createElement('tr');if(row.isYou)tr.className='you';for(const val of ['#'+row.rank,row.name+(row.isYou?' (you)':''),row.moves,duration(row.elapsedMs)]){const td=document.createElement('td');td.textContent=val;tr.append(td);}$('leader-rows').append(tr);}
  if(l.mine){const noun=current==='memory'?'turns':'moves';$('leader-summary').textContent=`You’re #${l.mine.rank} of ${l.count}. `+(l.mine.rank===1?'You lead today’s board.':l.gap>0?`${l.gap} ${noun} behind the leader.`:'Tied on moves; finish faster to take the lead.');}
  if(l.personalBest!==null)$('leader-best').textContent=`Your daily personal best: ${l.personalBest} ${current==='memory'?'turns':'moves'} (${difficulty}, across all days).`;
 }
 async function load(){
  const seq=++sequence;busy=true;error='';attempt=null;data=null;loaded=false;clearTimeout(hideTimer);updateState(null);leaderboard();
  try{const s=await request('/api/session');if(seq!==sequence||!active)return;session=s;loaded=true;if(s.user){const d=await request('/api/daily?game='+current+'&difficulty='+difficulty);if(seq!==sequence||!active)return;data=d;offset=d.serverNow-Date.now();updateState(d.attempt);$('display-name').value=s.user.profile?.display_name||'';}}
  catch(e){if(seq===sequence)error=e.message;}finally{if(seq===sequence){busy=false;header();leaderboard();}}
 }
 async function refreshBoard(){const seq=sequence;try{const d=await request('/api/daily?game='+current+'&difficulty='+difficulty);if(active&&seq===sequence){data=d;offset=d.serverNow-Date.now();updateState(d.attempt);leaderboard();header();}}catch(e){if(seq===sequence){error=e.message;header();}}}
 async function enter(){if(active)return;clearTimeout(timeout);timeout=null;if(state.flipped.length===2)state.flipped=[];save();active=true;difficulty=$('difficulty').value;await load();}
 function practice(){sequence++;clearTimeout(hideTimer);active=false;busy=false;attempt=null;state=null;header();choose(current);}
 async function start(){if(busy)return;busy=true;error='';header();const seq=sequence;try{const r=await request('/api/start','POST',{game:current,difficulty});if(seq!==sequence||!active)return;offset=r.serverNow-Date.now();updateState(r.attempt);}catch(e){error=e.message;}finally{if(seq===sequence){busy=false;header();}}}
 async function move(index){if(busy||!attempt||attempt.state.won)return;const seq=sequence;busy=true;error='';header();try{const r=await request('/api/move','POST',{attemptId:attempt.id,revision:attempt.revision,index});if(seq!==sequence||!active)return;offset=r.serverNow-Date.now();updateState(r.attempt);if(r.attempt.state.won)await refreshBoard();}catch(e){if(seq===sequence){error=e.message;await refreshBoard();}}finally{if(seq===sequence){busy=false;render();header();}}}
 window.ranked={get active(){return active;},afterRender:header,move,selectGame:game=>{current=game;return load();},selectDifficulty:value=>{difficulty=value;return load();}};
 $('practice-mode').onclick=practice;$('daily-mode').onclick=enter;$('ranked-start').onclick=start;$('ranked-refresh').onclick=load;
 $('profile-form').onsubmit=async e=>{e.preventDefault();if(busy)return;busy=true;error='';header();const seq=sequence;try{await request('/api/profile','PUT',{name:$('display-name').value});if(seq===sequence)await load();}catch(e){error=e.message;}finally{if(seq===sequence){busy=false;header();}}};
 $('ranked-signin').onclick=()=>{try{sessionStorage.setItem('pocket-daily-intent','1');}catch{}};
 setInterval(tick,1000);
 try{if(sessionStorage.getItem('pocket-daily-intent')){sessionStorage.removeItem('pocket-daily-intent');enter();}}catch{}
})();

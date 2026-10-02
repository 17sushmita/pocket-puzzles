(() => {
 const params=new URLSearchParams(location.search),game=params.get('game'),difficulty=params.get('difficulty');
 if(game&&Object.hasOwn(GAMES,game))choose(game);
 if(['easy','tricky'].includes(difficulty)&&difficulty!==state.difficulty){$('difficulty').value=difficulty;newPuzzle(difficulty);}
 if(params.get('mode')==='daily')window.ranked.openDaily();
 const notice=text=>{$('mobile-notice').textContent=text;};
 $('share-app').onclick=async()=>{
  const url=new URL('/',location.origin);url.searchParams.set('game',current);url.searchParams.set('difficulty',$('difficulty').value);if(window.ranked.active)url.searchParams.set('mode','daily');
  const isLocal=['localhost','127.0.0.1','[::1]'].includes(url.hostname);
  if(isLocal){$('share-url').value=url.href;$('share-help').textContent='This is a preview on this computer. Use the deployed Render link to share it with friends, or this computer’s network address on the same Wi-Fi.';$('share-dialog').showModal();return;}
  try{if(navigator.share){await navigator.share({title:'Pocket Puzzles',text:window.ranked.active?'Can you beat my score on today’s puzzle?':'Take a puzzle break with me.',url:url.href});return;}
   if(navigator.clipboard&&window.isSecureContext){await navigator.clipboard.writeText(url.href);notice('Link copied. Send it to a friend.');return;}
  }catch(e){if(e.name==='AbortError')return;}
  $('share-url').value=url.href;$('share-help').textContent='Send this link to a friend. It opens directly in their phone browser.';$('share-dialog').showModal();$('share-url').select();
 };
 $('share-close').onclick=()=>$('share-dialog').close();
 let installEvent;
 window.addEventListener('beforeinstallprompt',e=>{e.preventDefault();installEvent=e;$('install-app').hidden=false;});
 $('install-app').onclick=async()=>{if(installEvent){await installEvent.prompt();installEvent=null;$('install-app').hidden=true;}else notice('On iPhone: tap Share in Safari, then Add to Home Screen.');};
 if(/iPhone|iPad|iPod/.test(navigator.userAgent)&&!navigator.standalone){$('install-app').hidden=false;}
 if('serviceWorker' in navigator&&window.isSecureContext)navigator.serviceWorker.register('/sw.js').catch(()=>{});
 window.addEventListener('offline',()=>notice('You’re offline. Practice still works; ranked games need a connection.'));
 window.addEventListener('online',()=>notice('Back online. Refresh the leaderboard to resume your ranked attempt.'));
})();

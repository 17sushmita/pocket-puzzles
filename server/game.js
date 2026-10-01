export const games=['lights','slide','memory','flood'];
export const difficulties=['easy','tricky'];
export const neighbors=(i,n)=>[...(i%n?[i-1]:[]),...(i%n<n-1?[i+1]:[]),...(i>=n?[i-n]:[]),...(i<n*(n-1)?[i+n]:[])];
export function territory(b,n){const seen=new Set([0]),q=[0];for(let k=0;k<q.length;k++)for(const j of neighbors(q[k],n))if(!seen.has(j)&&b[j]===b[0]){seen.add(j);q.push(j);}return q;}
export function generate(game,difficulty){
 const n=game==='flood'?(difficulty==='easy'?6:9):game==='slide'?(difficulty==='easy'?3:4):game==='memory'?(difficulty==='easy'?4:6):(difficulty==='easy'?4:5);
 const random=max=>{const a=new Uint32Array(1);crypto.getRandomValues(a);return a[0]%max;};
 const shuffle=a=>{for(let i=a.length-1;i>0;i--){const j=random(i+1);[a[i],a[j]]=[a[j],a[i]];}return a;};
 let b=[];
 if(game==='lights'){b=Array(n*n).fill(0);for(const i of shuffle(Array.from({length:n*n},(_,i)=>i)).slice(0,n===4?5:11))for(const j of [i,...neighbors(i,n)])b[j]=1-b[j];if(!b.some(Boolean))for(const j of [0,...neighbors(0,n)])b[j]=1-b[j];}
 if(game==='slide'){b=Array.from({length:n*n},(_,i)=>(i+1)%(n*n));let empty=n*n-1,prev=-1;for(let k=0;k<(n===3?55:140);k++){const opts=neighbors(empty,n).filter(i=>i!==prev),next=opts[random(opts.length)];[b[empty],b[next]]=[b[next],b[empty]];prev=empty;empty=next;}if(b.every((v,i)=>v===(i+1)%(n*n))){const j=neighbors(empty,n)[0];[b[empty],b[j]]=[b[j],b[empty]];}}
 if(game==='memory')b=shuffle(Array.from({length:n*n},(_,i)=>Math.floor(i/2)));
 if(game==='flood'){b=Array.from({length:n*n},()=>random(6));if(b.every(v=>v===b[0]))b[b.length-1]=(b[0]+1)%6;}
 return {game,difficulty,n,board:b,matched:[],flipped:[],hideAt:0,moves:0,won:false};
}
export function advance(original,index,now){
 const s=structuredClone(original),b=s.board,n=s.n;
 if(s.won)throw new Error('This attempt is already complete.');
 if(!Number.isInteger(index)||index<0||index>=(s.game==='flood'?6:b.length))throw new Error('Invalid move.');
 if(s.game==='lights'){for(const j of [index,...neighbors(index,n)])b[j]=1-b[j];s.moves++;s.won=!b.some(Boolean);}
 if(s.game==='slide'){const empty=b.indexOf(0);if(!neighbors(empty,n).includes(index))throw new Error('Choose a tile next to the empty space.');[b[empty],b[index]]=[b[index],b[empty]];s.moves++;s.won=b.every((v,i)=>v===(i+1)%b.length);}
 if(s.game==='flood'){if(index===b[0])throw new Error('Choose a different color.');for(const j of territory(b,n))b[j]=index;s.moves++;s.won=b.every(v=>v===b[0]);}
 if(s.game==='memory'){
  if(s.flipped.length===2){if(now<s.hideAt)throw new Error('Wait for the cards to turn back over.');s.flipped=[];s.hideAt=0;}
  if(s.matched.includes(index)||s.flipped.includes(index))throw new Error('Choose a hidden card.');
  s.flipped.push(index);
  if(s.flipped.length===2){s.moves++;const [a,c]=s.flipped;if(b[a]===b[c]){s.matched.push(a,c);s.flipped=[];}else s.hideAt=now+850;}
  s.won=s.matched.length===b.length;
 }
 return s;
}
export function visibleState(s,now){
 const flipped=s.flipped.length===2&&now>=s.hideAt?[]:s.flipped;
 return {...s,flipped,board:s.board.map((v,i)=>s.game==='memory'&&!s.matched.includes(i)&&!flipped.includes(i)?null:v)};
}
export const dayKey=now=>new Date(now+330*60*1000).toISOString().slice(0,10);
export const nextReset=day=>Date.parse(day+'T00:00:00+05:30')+86400000;

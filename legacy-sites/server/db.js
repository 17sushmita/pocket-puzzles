export function database(env){if(!env.DB)throw new Error('Leaderboard database is not configured.');return {
 first:(sql,...args)=>env.DB.prepare(sql).bind(...args).first(),
 all:async(sql,...args)=>(await env.DB.prepare(sql).bind(...args).all()).results,
 run:(sql,...args)=>env.DB.prepare(sql).bind(...args).run()
};}

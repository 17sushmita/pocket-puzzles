import {DatabaseSync} from 'node:sqlite';
import {readFileSync,readdirSync} from 'node:fs';
export function localDatabase(path=':memory:'){
 const db=new DatabaseSync(path);db.exec('PRAGMA foreign_keys=ON');
 for(const file of readdirSync(new URL('../drizzle/',import.meta.url)).filter(f=>f.endsWith('.sql')).sort()){
  db.exec('CREATE TABLE IF NOT EXISTS _local_migrations (name TEXT PRIMARY KEY)');
  if(!db.prepare('SELECT name FROM _local_migrations WHERE name=?').get(file)){
   db.exec('BEGIN');try{db.exec(readFileSync(new URL('../drizzle/'+file,import.meta.url),'utf8'));db.prepare('INSERT INTO _local_migrations VALUES (?)').run(file);db.exec('COMMIT');}catch(e){db.exec('ROLLBACK');throw e;}
  }
 }
 return {
  raw:db,
  prepare(sql){
   const stmt=db.prepare(sql);
   return {bind(...args){return {
    async first(){return stmt.get(...args)||null;},
    async all(){return {results:stmt.all(...args)};},
    async run(){const r=stmt.run(...args);return {meta:{changes:r.changes}};}
   };}};
  }
 };
}

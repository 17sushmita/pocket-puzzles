import { sqliteTable, text, integer, uniqueIndex, index } from 'drizzle-orm/sqlite-core';
export const players=sqliteTable('players',{
 id:text('id').primaryKey(), displayName:text('display_name').notNull(), createdAt:integer('created_at').notNull()
});
export const challenges=sqliteTable('challenges',{
 id:text('id').primaryKey(), day:text('day').notNull(), game:text('game').notNull(), difficulty:text('difficulty').notNull(),
 puzzle:text('puzzle').notNull(), createdAt:integer('created_at').notNull()
}, t=>[uniqueIndex('idx_challenges_day_game_difficulty').on(t.day,t.game,t.difficulty)]);
export const attempts=sqliteTable('attempts',{
 id:text('id').primaryKey(),playerId:text('player_id').notNull().references(()=>players.id),challengeId:text('challenge_id').notNull().references(()=>challenges.id),
 state:text('state').notNull(),revision:integer('revision').notNull().default(0),lastIndex:integer('last_index'),
 startedAt:integer('started_at').notNull(),finishedAt:integer('finished_at'),moves:integer('moves').notNull().default(0),elapsedMs:integer('elapsed_ms')
}, t=>[uniqueIndex('idx_attempts_player_challenge').on(t.playerId,t.challengeId),index('idx_attempts_ranking').on(t.challengeId,t.finishedAt,t.moves,t.elapsedMs)]);

CREATE TABLE `attempts` (
	`id` text PRIMARY KEY NOT NULL,
	`player_id` text NOT NULL,
	`challenge_id` text NOT NULL,
	`state` text NOT NULL,
	`revision` integer DEFAULT 0 NOT NULL,
	`last_index` integer,
	`started_at` integer NOT NULL,
	`finished_at` integer,
	`moves` integer DEFAULT 0 NOT NULL,
	`elapsed_ms` integer,
	FOREIGN KEY (`player_id`) REFERENCES `players`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`challenge_id`) REFERENCES `challenges`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE UNIQUE INDEX `idx_attempts_player_challenge` ON `attempts` (`player_id`,`challenge_id`);--> statement-breakpoint
CREATE INDEX `idx_attempts_ranking` ON `attempts` (`challenge_id`,`finished_at`,`moves`,`elapsed_ms`);--> statement-breakpoint
CREATE TABLE `challenges` (
	`id` text PRIMARY KEY NOT NULL,
	`day` text NOT NULL,
	`game` text NOT NULL,
	`difficulty` text NOT NULL,
	`puzzle` text NOT NULL,
	`created_at` integer NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX `idx_challenges_day_game_difficulty` ON `challenges` (`day`,`game`,`difficulty`);--> statement-breakpoint
CREATE TABLE `players` (
	`id` text PRIMARY KEY NOT NULL,
	`display_name` text NOT NULL,
	`created_at` integer NOT NULL
);

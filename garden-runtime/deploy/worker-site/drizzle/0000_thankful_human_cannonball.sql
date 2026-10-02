CREATE TABLE IF NOT EXISTS `decisions` (
	`id` text PRIMARY KEY NOT NULL,
	`session_id` text NOT NULL,
	`proposal_id` text NOT NULL,
	`nonce` text NOT NULL,
	`created` integer NOT NULL,
	`decision` text NOT NULL,
	`tool` text NOT NULL,
	`receipt` text NOT NULL,
	`sequence` integer NOT NULL,
	FOREIGN KEY (`session_id`) REFERENCES `sessions`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE UNIQUE INDEX IF NOT EXISTS `session_sequence` ON `decisions` (`session_id`,`sequence`);--> statement-breakpoint
CREATE UNIQUE INDEX IF NOT EXISTS `session_nonce` ON `decisions` (`session_id`,`nonce`);--> statement-breakpoint
CREATE UNIQUE INDEX IF NOT EXISTS `session_proposal` ON `decisions` (`session_id`,`proposal_id`);--> statement-breakpoint
CREATE TABLE IF NOT EXISTS `sessions` (
	`id` text PRIMARY KEY NOT NULL,
	`human_hash` text NOT NULL,
	`agent_hash` text NOT NULL,
	`created` integer NOT NULL,
	`expires` integer NOT NULL,
	`revoked` integer DEFAULT 0 NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX IF NOT EXISTS `sessions_human_hash_unique` ON `sessions` (`human_hash`);--> statement-breakpoint
CREATE UNIQUE INDEX IF NOT EXISTS `sessions_agent_hash_unique` ON `sessions` (`agent_hash`);
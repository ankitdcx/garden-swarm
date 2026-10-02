CREATE TABLE `decisions` (
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
CREATE UNIQUE INDEX `session_sequence` ON `decisions` (`session_id`,`sequence`);--> statement-breakpoint
CREATE UNIQUE INDEX `session_nonce` ON `decisions` (`session_id`,`nonce`);--> statement-breakpoint
CREATE UNIQUE INDEX `session_proposal` ON `decisions` (`session_id`,`proposal_id`);--> statement-breakpoint
CREATE TABLE `sessions` (
	`id` text PRIMARY KEY NOT NULL,
	`human_hash` text NOT NULL,
	`agent_hash` text NOT NULL,
	`created` integer NOT NULL,
	`expires` integer NOT NULL,
	`revoked` integer DEFAULT 0 NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX `sessions_human_hash_unique` ON `sessions` (`human_hash`);--> statement-breakpoint
CREATE UNIQUE INDEX `sessions_agent_hash_unique` ON `sessions` (`agent_hash`);--> statement-breakpoint
CREATE TRIGGER decision_bound BEFORE INSERT ON decisions
BEGIN
 SELECT CASE WHEN NEW.decision='ALLOW' AND NOT EXISTS (SELECT 1 FROM sessions WHERE id=NEW.session_id AND expires>unixepoch() AND revoked=0) THEN RAISE(ABORT,'authority unavailable') END;
 SELECT CASE WHEN (SELECT COUNT(*) FROM decisions WHERE session_id=NEW.session_id)>=64 THEN RAISE(ABORT,'resource bound') END;
END;

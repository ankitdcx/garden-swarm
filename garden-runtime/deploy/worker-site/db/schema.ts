import { sqliteTable, text, integer, uniqueIndex } from 'drizzle-orm/sqlite-core';

export const sessions = sqliteTable('sessions', {
  id: text('id').primaryKey(),
  humanHash: text('human_hash').notNull().unique(),
  agentHash: text('agent_hash').notNull().unique(),
  created: integer('created').notNull(),
  expires: integer('expires').notNull(),
  revoked: integer('revoked').notNull().default(0),
});
export const decisions = sqliteTable('decisions', {
  id: text('id').primaryKey(),
  sessionId: text('session_id').notNull().references(() => sessions.id),
  proposalId: text('proposal_id').notNull(),
  nonce: text('nonce').notNull(),
  created: integer('created').notNull(),
  decision: text('decision').notNull(),
  tool: text('tool').notNull(),
  receipt: text('receipt').notNull(),
  sequence: integer('sequence').notNull(),
}, t => [uniqueIndex('session_sequence').on(t.sessionId,t.sequence),
         uniqueIndex('session_nonce').on(t.sessionId,t.nonce),
         uniqueIndex('session_proposal').on(t.sessionId,t.proposalId)]);

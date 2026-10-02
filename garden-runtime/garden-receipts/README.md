# Receipt contract

The external gate emits a structured receipt for each admitted or rejected
proposal. The record binds the exact proposal, gate policy digest, configured
Garden source anchors, evidence references, unknowns, assessments, authority,
human effects, decision, tool result, time and prior receipt digest. A keyed
authentication tag detects modification relative to the controller-held key.

Receipt integrity is not evidence truth, factual proof or deployment certification.
Only a separately protected checkpoint can establish which log head is current;
a local hash chain alone cannot defeat whole-log replacement or host rollback.
The demo exposes receipt copies. It never exposes receipt authentication keys or
accepts a receipt as an authorization token.

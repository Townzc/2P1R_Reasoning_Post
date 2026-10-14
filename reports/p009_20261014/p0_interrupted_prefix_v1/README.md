# P009 P0 original timing-gate stop — preserved failed attempt

The original call stopped after four complete base batches (128 saved raw rows).
No correct-969 output was attempted. The full ledger contains exactly four unit
intents and four matching done records: no missing or unacknowledged attempted
output. All 21 files / 670,700 bytes matched the original failed manifest; before
and after stopped-Volume listings matched. This is structural/raw-byte evidence,
not an accuracy or partial parity score. No original HF reference was rescored.

The observed full-batch maximum was 11.793591022491455 seconds. At the next gate,
the original rule forecast 1,582.9472081661224 total worker seconds, above its
1,170-second admission line / 1,200-second hard cap. The worker correctly stopped
before submitting batch five. Original failed claim, terminal, callback error,
cost reservation and source remain permanent. Provider stopped at 12:19:05 PDT
(19:19:05 UTC), with zero owned containers. This is an engineering time failure,
not a failed scientific parity comparison. That comparison is still unavailable.

The exact raw/ack/timing/failure bytes are in the projection archive. Only the
private runtime intent is omitted; its original SHA is retained in the full
failure manifest. Provider actor identity is projected out explicitly. No model,
collector, old oracle or test was repeated to create this packet.

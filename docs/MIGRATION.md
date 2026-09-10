# Move to another GPU server

**Current E012 preparation (2026-09-09):** use the E012 execution registration
and latest next-session handoff. C016 inputs are frozen; E011 completed and
failed its learning gate. The independently reconciled initial ledger has
16 receipts/5971 seconds used,1229 remaining,zero reservations. Do not restore
the historical5740 balance described in older sections. No E012 run or
checkpoint exists at this source milestone.

For E012 verify the latest GitHub commit on the local authenticated host, then
synchronize that exact commit by fetch or a verified bundle. Actual execution
requires `--expected-published-commit` matching this independently checked SHA;
an old clone's cached origin/main is insufficient evidence of current source.
The first arm is single_step. Following arms require raw-output verification,
published compact records and an independent per-file checkpoint backup.
Keep the existing16-receipt ledger prefix exact and append only the ordered
E012 receipts. No run auto-starts after cloning or booting an instance.

Start with `docs/NEXT_SESSION.md` for the latest shutdown handoff, required artifacts and the next discussion. These steps apply to a replacement machine or an instance clone; inspect what the clone actually preserved before reinstalling or transferring large files.

1. Commit and push code, configuration, compact run records and predictions from the current work session.
2. Clone this repository on the new server, or `git pull --ff-only` in an existing clean checkout. Check out the exact commit named in the run record when reproducing a run. For a bundle containing only `main`, use `git clone --branch main /path/to/project.bundle project`; such a bundle may omit a symbolic HEAD.
3. Recreate the isolated environment with the pinned requirements and bootstrap script; record new driver/GPU details.
4. Re-download base weights using the pinned model revision, or transfer the model cache separately. Git does not contain weights.
5. To resume optimizer training, separately transfer the checkpoint directory and verify its SHA-256 manifest. A code clone alone does not restore optimizer/model state. CPU/GPU RNG, optimizer, scheduler, sampler position and ledger must be restored by a supported resume implementation; otherwise start a new registered run rather than claiming exact resume.
6. Transfer the cumulative resource ledger when continuing the same approved budget. A fresh machine is not a new compute authorization.

Use the latest ledger from the active server or its verified local backup, and reconcile it with `reports/compute_accounting.json` and `docs/NEXT_SESSION.md`. Older clones may contain only the 737-second or 1173-second engineering balance; those are not the current balance after pilot jobs. The file lock is local to one server, so only one authorized GPU job may be active across all copies.

Keep SSH keys and host-specific paths outside Git. Small completed run artifacts are pulled back to the local repository and pushed to GitHub at each milestone. The training server does not need a GitHub write credential.

## When the GPU server cannot reach GitHub

Publish from the local authenticated workspace first. Create `git bundle create project.bundle main`, transfer that file over SSH, and on the destination run `git fetch /path/to/project.bundle main`. For a fresh destination, `git clone /path/to/project.bundle project` restores the complete bundled history. In an existing checkout, use `python scripts/sync_bundle.py --bundle /path/to/project.bundle --commit <published-40-character-sha>` after checking the published SHA locally. It refuses active/unresolved jobs, tracked edits, and differing untracked files; identical run logs can become tracked without losing ignored checkpoints. Verify the expected commit and tracked source/configuration before starting a job; do not launch while an asynchronous fetch is still pending.

For public model downloads when direct Hugging Face access fails, an optional mirror may supply bytes, but run `scripts/verify_model.py` against the digests pinned from the official API before use. Preserve licenses. Re-download or transfer the Hugging Face cache outside Git and verify again on the destination.

The first engineering runner saves model weights and tokenizer only. It cannot continue the exact optimizer trajectory; a later resume implementation needs optimizer/RNG/sampler checkpoints and a round-trip test. The original budget ledger belongs outside Git during execution, with a sanitized accounting snapshot committed after each milestone. Never reset a ledger to obtain more authorized time.

## When external SSH stalls before authentication

The replacement A800 session demonstrated that Jupyter terminal/file access can
remain available even when the external SSH connection receives no server banner.
Open the running instance's JupyterLab from its authenticated provider console,
confirm the GPU and cloned project state, and inspect the SSH service before
assuming that the GPU instance is broken. Do not weaken authentication or
certificate checks to restore access.

Upload the published Git bundle using Jupyter's file browser and use the same
`sync_bundle.py` checks. Run the finite queue under `nohup` with its existing
budget guard; closing a browser must not terminate the queue or its watchdog.
Use an independent authenticated browser for continued operation so the owner's
foreground browser activity does not interrupt terminal input.

Completed small records can be downloaded through Jupyter's authenticated file
interface. For large checkpoints, an authenticated HTTPS file transfer can resume
only after verifying that the server honors the requested byte range. Check each
file against the saved checkpoint SHA-256 manifest, then run `verify_artifact.py`
on the independent copy. A download attempt or a partial file is not a backup.

Keep connection tokens and transfer helpers with instance-specific settings outside
Git. If a hidden live ledger is not downloadable, export it to a temporary,
authenticated location outside the public checkout, download into the private
backup directory, verify the cumulative jobs and remove the temporary export.
Publish compact accounting separately. Never publish login tokens, SSH endpoints
or a live authentication file as part of an experiment record.


## Historical E011 relation engineering release

C015's five compact input files are fully tracked in
`runs/relation_engineering_c015_r1`; do not re-extract or replay older queues.
Follow [NEXT_SESSION.md](NEXT_SESSION.md) for current source,exact ledger hash,
pinned base and default-inspect launcher. One A80080GB,12GiB free after setup,
720-second process plus15-second guard. This paragraph described E011 before execution; its failed-gate checkpoint
is now independently backed up. Prior required weights/current cumulative ledger must remain independently
retained. A cloned instance grants no new budget and must not auto-run training.

# Move to another GPU server

1. Commit and push code, configuration, compact run records and predictions from the current work session.
2. Clone this repository on the new server, or `git pull --ff-only` in an existing clean checkout. Check out the exact commit named in the run record when reproducing a run.
3. Recreate the isolated environment with the pinned requirements and bootstrap script; record new driver/GPU details.
4. Re-download base weights using the pinned model revision, or transfer the model cache separately. Git does not contain weights.
5. To resume optimizer training, separately transfer the checkpoint directory and verify its SHA-256 manifest. A code clone alone does not restore optimizer/model state. CPU/GPU RNG, optimizer, scheduler, sampler position and ledger must be restored by a supported resume implementation; otherwise start a new registered run rather than claiming exact resume.
6. Transfer the cumulative resource ledger when continuing the same approved budget. A fresh machine is not a new compute authorization.

Keep SSH keys and host-specific paths outside Git. Small completed run artifacts are pulled back to the local repository and pushed to GitHub at each milestone. The training server does not need a GitHub write credential.

## When the GPU server cannot reach GitHub

Publish from the local authenticated workspace first. Create `git bundle create project.bundle main`, transfer that file over SSH, and on the destination run `git fetch /path/to/project.bundle main`. For a fresh destination, `git clone /path/to/project.bundle project` restores the complete bundled history. In an existing checkout, inspect local changes and advance the branch only after the fetch has completed successfully. Verify the expected commit and tracked source/configuration before starting a job; do not launch while an asynchronous fetch is still pending.

For public model downloads when direct Hugging Face access fails, an optional mirror may supply bytes, but run `scripts/verify_model.py` against the digests pinned from the official API before use. Preserve licenses. Re-download or transfer the Hugging Face cache outside Git and verify again on the destination.

The first engineering runner saves model weights and tokenizer only. It cannot continue the exact optimizer trajectory; a later resume implementation needs optimizer/RNG/sampler checkpoints and a round-trip test. The original budget ledger belongs outside Git during execution, with a sanitized accounting snapshot committed after each milestone. Never reset a ledger to obtain more authorized time.

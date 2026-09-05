# Move to another GPU server

1. Commit and push code, configuration, compact run records and predictions from the current work session.
2. Clone this repository on the new server, or `git pull --ff-only` in an existing clean checkout. Check out the exact commit named in the run record when reproducing a run.
3. Recreate the isolated environment with the pinned requirements and bootstrap script; record new driver/GPU details.
4. Re-download base weights using the pinned model revision, or transfer the model cache separately. Git does not contain weights.
5. To resume optimizer training, separately transfer the checkpoint directory and verify its SHA-256 manifest. A code clone alone does not restore optimizer/model state. CPU/GPU RNG, optimizer, scheduler, sampler position and ledger must be restored by a supported resume implementation; otherwise start a new registered run rather than claiming exact resume.
6. Transfer the cumulative resource ledger when continuing the same approved budget. A fresh machine is not a new compute authorization.

Keep SSH keys and host-specific paths outside Git. Small completed run artifacts are pulled back to the local repository and pushed to GitHub at each milestone. The training server does not need a GitHub write credential.

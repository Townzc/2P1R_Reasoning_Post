# Historical Modal weight cleanup authorized by 84404ebe

The deletion manifest names 112 exact leaves (514.408968 GiB) in three owner-authorized historical project directories. It must be published before deletion. Only model weights, downloaded model-weight cache files and manifest-identified training state are selected. All other files and directories are retained. No tar archive is opened.

EXISTING_METADATA.json preserves small, pre-existing hash proofs; no model or state is downloaded merely to hash it. BEFORE_INVENTORY.zip contains the complete historical volume directory listing. PREDELETE_ACTIVE_APPS.json maps every active app to a reviewed A8 request and its P012-only volume mount. Deletion uses exact published paths and recursive=False. The after-inventory and receipt must prove the removed path set equals the manifest and all retained regular files keep their size and timestamp.

Main-grid P/K8/R, all other P012 weights, and A8 weights remain. A8 weights require endpoint acceptance before their separate cleanup. Account and billing settings are unchanged.

Completed 2026-11-15T06:09:07.840458+00:00: all112 published leaves removed, 514.408968 GiB released. Full volume relisting proves no additional missing paths;173270 retained regular files keep their size and mtime. All16 .tar files and every other archive remain; no tar was opened.

Post-cleanup tangzhice volume total is704.733000 GiB. V′=796.149212 GiB includes the remaining allowance up to6 GiB for each of22 A8 checkpoints, counting existing checkpoint bytes once, plus1 GiB for future non-checkpoint files. The largest same-recipe checkpoint observed is5.766029 GiB. Expected daily net storage is$0, so the reserve through11/24 is$1. Official Modal pricing explicitly includes1 TiB/month and lists$0.09/GiB/month; see STORAGE_RESERVE.json.

The first complete post-cleanup UTC billing day is11/16, available after11/17 00:00 UTC. Before any new admission at that point, read actual net volume storage; more than$0.10 above prediction stops new admissions.11/15 is a partial-cleanup day, expected at most$0.46. The B/C admission helper now enforces this guard and the84404ebe formula;17 local classification/budget boundary checks pass.

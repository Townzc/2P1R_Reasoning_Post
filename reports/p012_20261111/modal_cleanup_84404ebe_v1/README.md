# Historical Modal weight cleanup authorized by 84404ebe

The deletion manifest names 112 exact leaves (514.408968 GiB) in three owner-authorized historical project directories. It must be published before deletion. Only model weights, downloaded model-weight cache files and manifest-identified training state are selected. All other files and directories are retained. No tar archive is opened.

EXISTING_METADATA.json preserves small, pre-existing hash proofs; no model or state is downloaded merely to hash it. BEFORE_INVENTORY.zip contains the complete historical volume directory listing. PREDELETE_ACTIVE_APPS.json maps every active app to a reviewed A8 request and its P012-only volume mount. Deletion uses exact published paths and recursive=False. The after-inventory and receipt must prove the removed path set equals the manifest and all retained regular files keep their size and timestamp.

Main-grid P/K8/R, all other P012 weights, and A8 weights remain. A8 weights require endpoint acceptance before their separate cleanup. Account and billing settings are unchanged.

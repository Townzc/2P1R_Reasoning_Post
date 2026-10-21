# Public inventory correction before first remote publication

The original MANIFEST.json writer opened its own empty destination before
listing files. Its eight payload entries are correct, but it also recorded an
invalid self-entry with zero bytes and the empty-file SHA. This original file
and the partial commit remain unchanged as failure evidence.

PUBLIC_MANIFEST.json is the authoritative inventory for this acceptance packet.
It binds all eight original payload files, this erratum and the original flawed
manifest as historical bytes, and excludes itself. No report, acceptance, actual
input, diagnostic source or scientific artifact was changed or recomputed.

The initial Git comparison list consequently compared nine distinct new files
with one duplicate comparison of the manifest (ten list entries); it was not
ten distinct files. The correction adds only two new files. No old scientific
archive verification was repeated. Existing recorded payload hashes are reused
in the corrected inventory; the original manifest's actual hash comes from that
completed Git comparison. The live diagnostic is unaffected.

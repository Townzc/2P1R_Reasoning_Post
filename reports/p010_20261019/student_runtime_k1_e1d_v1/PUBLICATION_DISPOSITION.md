# Candidate publication metadata correction

The initial candidate builder ran once. During the later prepublication Markdown formatting correction, the generic directory inventory accidentally included the existing MANIFEST.json itself. Git byte verification stopped at that self-reference before acceptance. The shell continued to the ordinary push despite this local metadata check failure; the preliminary commit remains in Git history. No model, upload, input builder, tests or scoring were repeated, and no runtime acceptance was written.

This correction removes only the self-reference and records this history. SPEC, all source/input/config bytes, tests and scientific scope are unchanged. INDEX binds the later corrected fixed commit after actual Git-member verification. The initial and intermediate manifest bytes remain in the private publication records. Four original copied source EOF warnings remain documented; the full whitespace check was not a pass.

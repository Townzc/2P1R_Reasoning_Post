# Exact archive part-size wording — 2026-10-21

The immutable actual input packet at
`20044d50cee1acbef0b1aa17ed559e8f0311d98a` retains its original bytes.
Its archive consists of ten parts totaling419,240,400bytes. Parts000–008 are
exactly41,943,040bytes each (**40MiB**); part009 is41,753,040bytes. Thus the correct
wording is **at most40MiB**, correcting “below/under40MiB” in the original copy
README and initial A1 request. Exact sizes in ARCHIVE_READBACK and PUBLIC_MANIFEST
were already correct. No archive, manifest, data, source, dose, test or scientific
result was changed or rerun. This is a dated metadata clarification only.

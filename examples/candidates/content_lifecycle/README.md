# Historical content-lifecycle replay candidate

These 13 tests come from the owner's archived TRAE run
`20260821T163455Z-content_lifecycle-8aafd9`, ported to the version-2 workbench.
The original source hashes are retained in `source-provenance.json`.

Changes: explicit case markers, shared frozen-data loading, per-instance reset authorization,
removal of UI-level global reset, and an explicit outcome assertion in the minimum-title check.
The original main flow did not upload an image; its label was corrected. Real image upload and
restart persistence are covered separately by maintained baseline tests.

This is **not a fresh TRAE generation**, and archived host/model versions are not known.
The port has been reviewed by the coding assistant; **maintainer approval is still pending**.
It remains under `examples/candidates/`, not `examples/approved/`.

The CSV contains 20 synthetic data rows, not 20 independent tests. `expected_valid` describes
the conjunction of title, body and comment length rules for this lifecycle dataset. Individual
tests still assert the specific outcomes in the plan rather than blindly using that flag.

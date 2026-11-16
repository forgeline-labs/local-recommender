# Normative ambiguity resolutions

The implementation and the public tests follow the audit resolutions of spec
v0.1.4 (§8). They are restated here so the expected behaviour is visible next
to the tests.

1. A file larger than 1048576 bytes exits `2` with no data output.
2. A missing file or missing parent directory exits `3` (AC-12).
3. Numeric or otherwise non-string `user`/`item` values raise `ValueError` in
   the library and exit `2` through the CLI.
4. Reordering input preserves published items, order and scores; numeric
   comparison uses absolute tolerance 0.000001.
5. The final score is rounded half-even to six decimal places; individual terms
   are never rounded before summation.
6. The 1048576-byte limit is inclusive and measured before parsing; JSON
   whitespace counts.
7. A readable file with invalid JSON exits `2`; unreadable input or file I/O
   failure exits `3`. Precedence between other combined errors is out of scope.
8. Pairs are deduplicated by exact `(user, item)`, independent of key order in
   the JSON object.
9. Candidates whose score is mathematically zero are filtered; no arbitrary
   epsilon is used. Positive candidates do not round to zero under the declared
   limits.
10. Deduplication uses the exact pair value, not dictionary identity or order.
11. An incomplete command or a missing required argument exits `2`.
12. HTTP is out of scope for this product.
13. Cold start is defined: unknown user, or no positive candidates, yields `[]`
    with no popularity fallback.
14. Physical disk failure and simultaneous writers are out of scope; the
    library itself has no persistence.

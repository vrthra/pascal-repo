# ISO 7185 Pascal Corpus

100 `.pas` files collected from public GitHub repositories, each checked against `validate.py` (the dialect guard in this folder) plus a few additional dialect checks added during verification. All 100 files pass cleanly.

## Scope and honesty about what "conforms" means here

`validate.py`'s own docstring says it explicitly: it is "not a full ISO 7185 parser," just a regex-based guard for common FreePascal/Delphi/Object-Pascal dialect clues (`unit`, `interface`/`implementation`, `try/except`, `class`/`property`, sized `string[n]`, `$mode` directives, `!` negation, etc.). Passing it means "no detected sign of non-ISO dialect drift" — not "verified valid by a conformant ISO 7185 compiler."

While curating, I found the base `validate.py` ruleset misses a few other well-known non-ISO-7185 constructs, and cross-checked the final list for those too:

- `module X;` — a Pascal-P6-specific extension for separate compilation, distinct from `unit`, not in ISO 7185. (One file, `extend.pas`, literally documents itself as "Language extension routines... beyond the base ISO 7185 specification.")
- `const` as a parameter-passing mode (e.g. `function f(const s: string)`) — a Borland/Extended-Pascal addition; ISO 7185 only has value and `var` parameters.
- `shl` / `shr` / `xor` — bitwise/boolean operators not defined in ISO 7185.
- `otherwise` as a case-statement default clause — added in later dialects, not ISO 7185.
- `$FF`-style hexadecimal integer literals — ISO 7185 has no hex literal syntax.

25 of my first 100 picks tripped one of these (mostly Pascal-P6's own compiler-internals, which uses its own extended dialect for its `source/`, `pc/`, and `libs/` internals). I dropped all 25 and backfilled with 25 verified-clean replacements. The final 100 pass both `validate.py` (exit code 0, 0 violations) and this extended check.

## Where the files came from

| Source repo | Files | What it is |
|---|---|---|
| [samiam95124/Pascal-P6](https://github.com/samiam95124/Pascal-P6) | 46 | 6th-generation Pascal-P compiler/toolchain (Wirth's original ETH Zurich compiler, updated to ISO 7185 by Scott A. Moore/Franco): compiler/interpreter sources (`pcom.pas`, `pint.pas`), games (`chess.pas`, `checkers.pas`, `backgammon.pas`, `pong.pas`), and sample/benchmark programs (`drystone.pas`, `fbench.pas`, `qsort.pas`, `roman.pas`). Internal build-system files that use Pascal-P6's own `module` extension were excluded. |
| [samiam95124/Pascal-P5](https://github.com/samiam95124/Pascal-P5) | 18 | 5th-generation predecessor to P6. Same family of compiler sources and sample programs (P5 doesn't use the `module` extension, so more of it survived screening intact). |
| [StanfordPascal/Pascal](https://github.com/StanfordPascal/Pascal) | 23 | Classic Pascal compiler test programs, including `iso7185pat.pas` (the "Pascal Acceptance Test" — a single program that exercises essentially every ISO 7185 language feature), `iso7185.pas`, historical compiler snapshots (`pas1979.pas`), and dozens of individual `TESTxxx.pas` feature tests (sets, files, records, real numbers, etc.). |
| [Leporacanthicus/lacsap](https://github.com/Leporacanthicus/lacsap) | 11 | LLVM-based Pascal compiler whose test suite claims ISO 7185 Acceptance Test conformance; includes benchmarks (`dhry.pas`, `sieve.pas`) and small single-feature tests (arrays, files). |
| [komninoschatzipapas/psi](https://github.com/komninoschatzipapas/psi) | 2 | WIP ISO 7185 Pascal interpreter test fixtures. |

Total: **100 files**, ~5.5 MB, ~150,000 lines. Layout: `iso7185-pascal-corpus/<repo-name>/<original upstream path>`.

## Method

1. Searched GitHub for repositories built explicitly around ISO 7185 Pascal (compilers, interpreters, conformance suites).
2. Shallow-cloned 5 candidate repos — 1,438 `.pas` files total.
3. Ran `validate.py --json`: 111 files flagged (mostly FreePascal `{$mode}`/`unit` fixtures), 1,327 passed.
4. Excluded, before sampling, categories known by directory/naming convention to contain *intentionally invalid* programs that the regex guard can't catch:
   - `standard_tests/` in Pascal-P5/P6 — an official-style 400-file-per-repo ISO 7185 conformance suite that deliberately mixes valid and invalid programs to test that a compiler *rejects* bad input (e.g. `iso7185prt0300.pas` is titled "Missing 'procedure'" and is supposed to fail to compile).
   - `comperr`/`CompErr` directories and files with "err"/"fail"/"crash" in the name (compiler-error/diagnostic fixtures).
   - Harness/expected-output fixtures (not source programs).
5. Deduplicated by content hash and dropped near-empty stubs (<80 bytes) — 410 unique legitimate candidates remained.
6. Hand-curated 100 for size and diversity across the 5 repos.
7. Verification pass: re-ran `validate.py` on the 100 (clean), then wrote extra regex checks for `module`, `const`-params, `shl`/`shr`/`xor`, `otherwise`, and hex literals (reusing `validate.py`'s own comment/string-masking so checks don't false-positive inside comments/strings). This caught the 25 files described above; they were swapped for 25 verified-clean replacements from the remaining candidate pool.
8. Final check: `validate.py` on the actual 100 files copied into this folder → **exit code 0**; extended check → **0 flagged**.

## Licensing

- Pascal-P6: BSD-style (Copyright Scott A. Franco).
- Pascal-P5: license terms are referenced as being in `doc/the_p5_compiler.docx` in that repo (not reproduced here) — check upstream before redistribution.
- lacsap: ISC-style permissive (Copyright Mats Petersson).
- psi: MIT.
- StanfordPascal/Pascal: no LICENSE file found in the repo at the time of this pull — treat as "all rights reserved" unless confirmed otherwise with the maintainer.

This corpus is for local validation/testing use. Check each upstream repo's license before redistributing further.

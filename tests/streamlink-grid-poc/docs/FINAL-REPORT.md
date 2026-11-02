# Independent H.264 / MPEG-TS compatibility result

## Outcome

One standards-based over-rejection was reproduced and corrected: POC type 2 previously rejected every consecutive non-reference pair, while H.264 prohibits only the pair that produces duplicate POC. The new check allows distinct POC values and preserves the duplicate-POC rejection. All other unsupported/uncertain syntax remains fail-closed.

PCR recovery for up to two seconds remains a file-timeline repair only. The deterministic 231 ms path passes independent TS/PES validation and FFmpeg decoding, but does not promise wall-clock packet pacing or prove the source contained no lost media.

## User-reported issue status

| Issue | Status | Evidence / limit |
|---|---|---|
| V3 reorder timing / reorder bound | PARTIAL | Current uses Grid composition for PTS and retains POC/display-order and DPB-bound checks. Same B-frame fixture matches FFprobe. Reporter's patch/capture is unavailable; arbitrary V3 input unverified. |
| V5 picture order conflict | UNVERIFIED as reporter case | Current rejects contradictory POC vs Grid composition. Same generated B-frame fixture is correct; exact reporter input absent. |
| V8 frame_num 119→1 | UNVERIFIED as reporter case | The transition is not normal wrap for MaxFrameNum 128 and remains rejected when gaps are forbidden. Grid continuity does not prove H.264 reference continuity. Original SPS/reference/AU unavailable. |
| V8 231 ms PCR gap | PARTIAL | Bounded PCR-only interpolation and independent 231 ms TS/full decode pass. No real V8 capture or real-time pacing test. |

## Tests and tool checks

* Focused H.264/TS tests: **139 passed, 2 skipped**.
* Full modular source suite (excluding untouched untracked `tests/test_suffix_latejoin.py`): **733 passed, 2 skipped**.
* Static bundle suite (same exclusion): **724 passed, 2 skipped**.
* Skip reason: local FFmpeg does not expose `libopenh264`; tests requiring that encoder for real POC type 2 fixtures skipped. These were existing environment skips, not newly hidden failures.
* Ruff check: passed.
* Ruff format: 52 tracked source/tool/test files passed. A whole-tree format check also reported the pre-existing untracked `tests/test_suffix_latejoin.py`; that file was not edited, staged, or used in the suite.
* `compileall`, deterministic bundle `--check`, SHA check, and `git diff --check`: passed.
* New bundle SHA-256: `d303a80c5a972702cc249d9488f77071e60763d7e3fc5e49d46dca053c145f25`.
* No live broadcast/long recording was performed.

## Remaining scope and release decision

POC type 1, production MMCO5, arbitrary reference-DPB validation, real-time mux pacing, the reporter's exact V3/V5/V8 samples, and broad live compatibility remain unverified or unsupported. Do not label the reporter's exact failures fixed without their input. The q=32/1080p profile changes predated this task and are kept separate in Git history.

**Release:** Beta only; not a new Stable declaration. H.264 correction is a narrow compatibility improvement backed by syntax probes, with full suite parity. Live stability is not established by this offline work.

# H.264 reference, POC, DPB and timing conformance

Audited source: `soop_grid/h264clock.py`, `soop_grid/media.py`. Normative reference: [ITU-T H.264 (08/2024)](https://www.itu.int/rec/T-REC-H.264-202408-S), clauses 7.4.2.1, 7.4.3, 8.2.1, 8.2.5, and Annex C. This is an implementation-subset assessment, not full decoder conformance.

## Production invariants

* Input is bounded Annex-B H.264. Parsed syntax is validated before an AU is committed; `H264Clock.inspect()` snapshots and rolls back mutable state after rejection.
* Production DTS is rescaled Grid `startTime`; PTS is rescaled `startTime + composition`, with a common origin. POC is used to check picture/display order, never converted to an assumed frame duration.
* VCL payload is carried unchanged. Startup may prepend active SPS/PPS to make the output independently decodable; this is parameter-set framing, not VCL rewriting.
* Each accepted Grid video chunk must describe one supported picture. DTS must increase; PTS must be unique and agree with POC order within the bounded reorder window.

## POC types and boundaries

| Type | Implemented order state | Evidence level on documented subset | Remaining boundary |
|---:|---|---|---|
| 0 | Previous-reference POC LSB/MSB wrap; IDR epoch; reference marking; bounded reorder | Parser + offline StreamIO/TS/decode + historical short self-broadcast with B pictures | MMCO 5 remains rejected; unusual DPB transitions and current-hash live run unverified |
| 1 | `FrameNumOffset`, `AbsFrameNum`, cycle offsets, non-reference offset and slice deltas | Parser + offline valid B-picture stream + historical short live no-reorder self-broadcast | Live B-picture, arbitrary cycles/deltas and MMCO 5 unverified |
| 2 | `FrameNumOffset` and `frame_num`; zero-reorder subset | Parser + offline decode + historical short low-delay/no-B self-broadcast | Reorder unsupported; adjacent non-reference picture sequence forbidden by SPS type-2 constraints; MMCO 5 unverified |

`gaps_in_frame_num_value_allowed_flag=1` permits the decoder's normative non-existing reference-picture process; it is not proof that the transport delivered those coded pictures. This receiver does not invent VCL AUs. When gaps are disallowed, a reference-state successor mismatch fails with `h264_frame_num_gap`. For `MaxFrameNum=128`, 119→1 is not a modulo wrap; normal wrap is 127→0. Exact source SPS, slice/reference state and AU bytes from the community report are unavailable.

## MMCO 5

The parser detects MMCO 5 and some internal POC/reference reset bookkeeping exists. Production rejects the Grid timing transition as `h264_grid_mmco5_unverified`; it is not claimed supported. Full validation must establish the reset picture's decoded-reference state, subsequent `PrevRefFrameNum`, POC/FrameNumOffset and Grid composition output epoch together. Existing unit checks of isolated helper arithmetic do not satisfy this gate.

## Other explicit limits

Interlace/field pictures, FMO, unsupported slice/reference syntax, unsupported profiles, midstream codec changes, low-delay HRD and nonzero `pic_struct` are not in the supported subset. VUI reorder limits are checked against level/DPB bounds. HRD/SEI syntax is validated where implemented, but HRD delay does not supply production timestamps. POC/composition conflict, duplicate PTS, invalid reorder bounds and missing required parameter sets fail closed.

## Evidence scope

The historical self-broadcast evidence in `POC_GRID_LIVE_VALIDATION.md` belongs to bundle SHA `e1a1433bbcfb67febb37e43b7e92f2761c3f1cd58b4119dfbaa44c5dc0f6029b`, not the current `5c1657…` bundle. It establishes short captured intervals only. The exact V3/V5/V8 user inputs remain unverified. Current exact-bundle unit and bundle results are in `ENDURANCE_RESULT.md`.

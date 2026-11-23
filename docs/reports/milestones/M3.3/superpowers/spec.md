# M3.3 — Specification: Capped Capture-to-Transcript-to-Search Pilot & Hybrid Legacy-Compatible Collector Upgrade

- **Task ID:** `M3.3`
- **Primary Owners:** Nguyễn Việt Nguyên (`N`) & Trần Đình Khương (`K`) (shared integration & 50/50 sample inspection)
- **Prerequisite Gates / Tasks:** `G2 = PASS` (`M2.G`), `M3.1 = COMPLETE`, `M3.2 = COMPLETE`
- **Requirement Source:** [TikTok_AI_Engine_Milestone.md](../../../../planning/TikTok_AI_Engine_Milestone.md) (`M3.3`, lines 56, 99)
- **Revision History:**
  - `2026-11-20` (Phase 1): Bounded `M3.3` capture -> CPU ASR -> Dual-Sink Gold -> BM25 -> searchability orchestrator & host `.venv` `faster-whisper` verification.
  - `2026-11-23` (Phase 2, authored by `K`): Hybrid `TikTokApi` + `yt-dlp` collector upgrade adapting the `TrggTin/21KHDL-TikTok-Analytics` `itemStruct`/comment schema, authenticated `64 kbps` `.mp3` extraction, curated F&B `--auto-creators`, crash-safe `--resume`, and `--preflight-only` home execution readiness.

---

## 1. Scope & Hard Ceilings (Preserved Baseline)

Prepare and execute (when live network tools and `MS_TOKEN` are available) the bounded end-to-end fresh-data pilot under a strict `USD 0` local CPU budget:

1. **Collection Bounds (`M3.2` worker):** Maximum `5` creators, `50` candidate fresh videos (`<= 120` days, excluding all `70,996` historical IDs), `30` successful videos, `60.0` audio minutes, `1,000` comments (`<= 50` comments per video), and `1` bounded session (`<= 7,200` seconds / `2` hours).
2. **Measured CPU ASR Pilot Cap:** Transcribe **at most `10` videos** and **at most `20.0` audio minutes** before searchability verification. Enforce `0.0 <= start_sec < end_sec` on `RawWhisperSegment` outputs and leave un-transcribed or audio-missing records untouched (`transcript=""`, `whisper_segments=[]`).
3. **Dual-Sink Gold Ingest (`M3.1`) & Searchability Probe:** Ingest the pilot batch atop `data/corpus/20261118_taxonomy_fix_v1` into a new versioned output snapshot (never mutating historical bytes), build a versioned BM25 index (`BM25Index.build`), and verify that freshly transcribed videos are retrievable via `HybridRetrievalService` with exact source `video_id` matching (`>= 5` real non-synthetic transcribed fresh videos required for pilot `PASS`).
4. **Honest Mode Separation & Fail-Closed Status:**
   - `--mode dry_run_fixture`: verifies wiring, caps, metrics, disk/RAM/RTF measurement, and 50/50 `K`/`N` inspection sheet generation using synthetic fixtures (`is_synthetic_fixture=True`, `pilot_status="FIXTURE_DRY_RUN_ONLY"`). Never counts as live `M3.3` acceptance.
   - `--mode live_pilot`: requires `--allow-live-network`, `MS_TOKEN`, `yt-dlp`, `ffmpeg`, and `faster-whisper`. If host tools, credentials, anti-bot challenges, or TikTok network yield fail (`< 5` real fresh searchable transcribed videos), emit `pilot_status="BLOCKED"` honestly without fake replacement data.
5. **Equal Sample Inspection (`50% K / 50% N`):** Export `sample_inspection_sheet.jsonl` assigning half of succeeded videos to `K` and half to `N` with `human_verified=false` placeholders.

---

## 2. Phase 2 Architectural Upgrade (`2026-11-23`) — Adapting `21KHDL-TikTok-Analytics` Crawling Capabilities

### 2.1 Unified `itemStruct` & `yt-dlp` Schema Mapping (`pipelines/crawl_incremental/mappers.py`)

Adapt the field-level schema knowledge from `TrggTin/21KHDL-TikTok-Analytics` (`data/raw/*.json`, `data/interim/final_raw_videos.csv`, and `pipelines/build_gold_corpus/builder.py`) without copying frozen vendored code or custom stealth scripts:

- **`map_tiktok_item_struct_to_detail(raw, *, fallback_vid="", fallback_handle="") -> dict[str, Any]`:**
  - Maps native TikTok `itemStruct` payloads (`id`, `createTime`, `desc`, `author.{id, uniqueId, nickname}`, `authorStats.followerCount`, `video.duration`, `statsV2.{playCount, diggCount, commentCount, shareCount, collectCount}` with `stats.*` fallback, `challenges`/`contents`/`textExtra` hashtags).
  - Preserves commercial and venue metadata previously dropped by `yt-dlp`-only mapping: `isAd -> is_ad`, `isECVideo -> is_ec_video`, `playlistId -> playlist_id`, and `poi.{id, name, address, city, ttTypeNameTiny} -> poi_{id, name, address, city, category_tiny}` (converting blank/`"others"`/`"null"` strings to `None`).
- **`map_tiktok_comment_to_input(raw, *, canonical_vid, idx) -> dict[str, Any] | None`:**
  - Normalizes both `TikTokApi` comment dicts (`cid`, `user.{unique_id, uniqueId}`, `text`, `digg_count`, `reply_comment_total`) and `yt-dlp` comment dicts (`id`, `author`, `text`, `like_count`, `reply_count`).
  - Rejects empty/whitespace-only comments while **preserving raw unstripped `text`** (including leading/trailing whitespace) so `CommentRecord.original_text` and `M5.2` Unicode `NFC` character offsets remain exact.
- **`map_ytdlp_json_to_detail(raw, *, candidate) -> tuple[dict[str, Any], list[dict[str, Any]]]`:**
  - Upgrades `yt-dlp` JSON extraction to populate `collect_count` (`collect_count` / `save_count`), `share_count` (`repost_count` / `share_count`), comment `reply_count` (including counting child replies via `parent` IDs when `yt-dlp` emits flat comment lists), and any `is_ad`, `is_ec_video`, `playlist_id`, or `poi` fields exposed by the extractor.

### 2.2 Pluggable `CollectorBackend` (`auto` | `tiktokapi` | `ytdlp`) & Fail-Closed Anti-Bot Gate (`pipelines/crawl_incremental/providers.py`, `worker.py`)

- **`CollectorBackend = Literal["auto", "tiktokapi", "ytdlp"]` (default `"auto"`):**
  1. **`TikTokApiCollectorProvider` (`backend="tiktokapi"`):** Lazily imports the official `TikTokApi` Python package (never bundling vendored `stealth/js` overrides). Runs bounded async calls (`ms_tokens=[ms_token]`, configurable `timeout_sec`) to discover creator videos (`user.videos(count=max_per_creator)`), inspect video `as_dict` `itemStruct`, and fetch comments (`video.comments(count=max_comments)`). Raises `LiveNetworkDisabledError` if `TikTokApi` is not installed when explicitly requested.
  2. **`LiveTikTokCollectorProvider` (`backend="ytdlp"`):** Passes `--add-header "Cookie: msToken=<ms_token>"` and optional `--cookies <cookies_file>` to `yt-dlp` discovery and detail/comment extraction, delegating normalization to `map_ytdlp_json_to_detail`.
  3. **`AutoHybridTikTokCollectorProvider` (`backend="auto"`):** Uses `TikTokApiCollectorProvider` as primary when `TikTokApi` is importable on the host, automatically falling back per-call to `LiveTikTokCollectorProvider` (`ytdlp`) on `TransientCollectorError` or Playwright browser-launch/runtime unavailability; if the primary detail/comment fetch yields `0` comments for a video reporting `comment_count > 0`, attempts secondary `fetch_comments` once. When `TikTokApi` is not installed on the host, routes directly to `LiveTikTokCollectorProvider` (`ytdlp`). Tracks `backends_used: list[str]` for provenance.
- **Strict Anti-Bot / CAPTCHA Boundary (`AntiBotChallengeError`):**
  - Any CAPTCHA, human-verification challenge, or explicit anti-bot gate surfaced by `TikTokApi` or `yt-dlp` raises `AntiBotChallengeError` (distinct from `TransientCollectorError`).
  - Neither `AutoHybridTikTokCollectorProvider` nor `BoundedIncrementalCollector` retries or switches backends to evade `AntiBotChallengeError`. `BoundedIncrementalCollector` records `status="failed"`, `attempts=1`, sanitized `reason="anti_bot_challenge_blocked: ..."`, and halts the live loop (`stopped_reason="anti_bot_challenge_blocked"`).

### 2.3 Authenticated `64 kbps` Audio Extraction & Credential Redaction (`crawler_service.py`, `providers.py`, `worker.py`)

- `download_audio_mp3_64k(tiktok_url, output_mp3, *, ms_token="", cookies_file=None, timeout_sec=45)` and `YtDlpAudioConverter64k(allow_live_network=False, ms_token="", cookies_file=None)` forward `Cookie: msToken=<ms_token>` and optional `--cookies <cookies_file>` to `yt-dlp` so `64 kbps` `.mp3` downloads do not fail with unauthenticated `HTTP 403` errors while never downloading full `.mp4` video files.
- `_sanitize_reason` in `worker.py` redacts `ms_token`, `msToken`, `sessionid`, `Cookie`, and `--cookies <path>` arguments before writing any receipt or manifest.

### 2.4 Turnkey Home Execution Controls (`--auto-creators`, `--resume`, `--preflight-only`, `.env` Auto-Load)

- **`load_dotenv_if_present(dotenv_path=Path(".env"))`:** Reads `KEY=VALUE` pairs from gitignored `.env` into `os.environ` only for unset keys (`MS_TOKEN`, `TIKTOK_COOKIES_FILE`) so running the CLI directly on a home machine picks up `.env` automatically without logging secrets.
- **`select_curated_fnb_creators(base_corpus_dir, *, top_k=5) -> list[str]`:** Reads `dim_creators.parquet` (`264` curated F&B creators from `21KHDL-TikTok-Analytics`), filters non-blank `unique_id`, sorts deterministically by `(-avg_videos_per_week, -sample_video_count, -follower_count, unique_id)`, and merges with any explicit `--creator` flags up to `max_creators` (`<= 5`).
- **`--resume` in `pipelines.pilot_m3_3`:** Adds `resume: bool = False` to `M33PilotConfig` and forwards it to `BoundedIncrementalCollector.run(..., resume=config.resume)` so interrupted home sessions resume from `collector_checkpoint.json`.
- **`--preflight-only` in `pipelines.pilot_m3_3`:** Executes zero network requests; checks `MS_TOKEN`, `cookies_file` (if set), `yt-dlp`, `ffmpeg`, `faster-whisper`, optional `TikTokApi` + Playwright availability, `70,996` historical IDs, and resolved creator handles, returning a structured JSON readiness summary (`ready_for_live_pilot`, `resolved_backend`, `selected_creators`, `blocker_reasons`).
- **Provenance Fields:** Additive defaulted fields `collector_backend_requested: str = "auto"` and `collector_backends_used: list[str] = Field(default_factory=list)` on `CrawlManifest` and `CollectionSummaryReceipt` preserve full backward compatibility with existing receipts.

# Architecture Context — Speedlog

## High-level architecture
Two logical layers inside one process:

```
┌────────────────────────────────────────────────────────────┐
│ UI Layer (Qt main thread)                                  │
│  - QSystemTrayIcon (live speed)                            │
│  - MainWindow: LiveSpeedWidget | ReportsPage | Filters     │
│  - PDF Export dialog                                       │
└──────────────▲───────────────────────────┬─────────────────┘
        Qt Signals (speed_sampled,         │ repository calls
        segment_closed, session_changed)   │ (read-only queries)
┌──────────────┴───────────────────────────▼─────────────────┐
│ Collector Layer (QThread)                                  │
│  Sampler(1s, psutil) → Smoother(EMA/SMA) → Segmenter       │
│  (bucket + hysteresis) → Repository(SQLite writes)         │
│  ConnectivityWatcher → session start/end                   │
└────────────────────────────────────────────────────────────┘
                        │
                   SQLite file
        ~/Library/Application Support/Speedlog/data.db
```

## Threading rules (critical)
- Exactly ONE collector `QThread`. All psutil sampling and DB **writes** happen there.
- UI thread does DB **reads only** (reports queries). SQLite opened with
  `check_same_thread=False` is forbidden — instead each thread owns its own connection.
- Collector → UI communication is ONLY via Qt signals (thread-safe). Never touch widgets
  from the collector thread.
- WAL mode enabled (`PRAGMA journal_mode=WAL`) so reads don't block writes.

## Package layout
```
app/
├── main.py                  # entry point, QApplication bootstrap
├── config.py                # constants, paths, settings
├── formatting.py            # format_speed() shared by tray, table, PDF
├── logging_setup.py
├── collector/
│   ├── sampler.py           # psutil per-interface byte counters, 1s tick
│   ├── smoother.py          # moving average over N samples
│   ├── segmenter.py         # bucketing + hysteresis state machine
│   ├── connectivity.py      # online/offline detection
│   └── service.py           # CollectorService(QThread) wiring it all
├── data/
│   ├── db.py                # connection factory, migrations, PRAGMAs
│   ├── models.py            # dataclasses: SpeedRecord, Session
│   └── repository.py        # all SQL lives here (only here)
├── ui/
│   ├── tray.py
│   ├── main_window.py
│   ├── live_view.py
│   ├── reports/
│   │   ├── table_model.py   # QAbstractTableModel
│   │   ├── reports_page.py  # table + pagination controls
│   │   └── filter_panel.py
│   └── styles.qss
├── export/
│   └── pdf_report.py        # reportlab generator
└── platform/
    ├── autostart_macos.py   # LaunchAgent plist install/remove
    └── userinfo.py          # full user name (cross-platform)
tests/
```

## Database schema
```sql
CREATE TABLE sessions (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  start_ts   INTEGER NOT NULL,          -- UTC epoch seconds
  end_ts     INTEGER,                   -- NULL while open
  end_reason TEXT                       -- 'disconnect' | 'quit' | NULL
);

CREATE TABLE speed_records (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id    INTEGER NOT NULL REFERENCES sessions(id),
  start_ts      INTEGER NOT NULL,       -- UTC epoch seconds
  end_ts        INTEGER NOT NULL,
  download_bps  REAL NOT NULL,          -- bytes/sec, representative (mean of segment)
  upload_bps    REAL NOT NULL
);

CREATE INDEX idx_records_start ON speed_records(start_ts);
CREATE INDEX idx_records_session ON speed_records(session_id);

CREATE TABLE schema_version (version INTEGER NOT NULL);
```
- Store raw bytes/sec (REAL). Format to MB/s (SI, 1 MB = 1,000,000 bytes) only in UI/PDF.
- All timestamps UTC. Convert to local timezone in the UI layer only.

## Segmenter algorithm (the heart of F2)
State machine, evaluated every 1s tick with the SMOOTHED download & upload values:

```
Parameters (config.py):
  SAMPLE_INTERVAL   = 1.0 s
  SMOOTH_WINDOW     = 5 samples (simple moving average)
  BAND_TOLERANCE    = max(10% of segment mean, 0.25 MB/s absolute floor)
  HYSTERESIS_TICKS  = 5   # consecutive out-of-band samples required to split
  MIN_SEGMENT_SECS  = 5   # segments shorter than this merge into neighbor

State: current_segment {start_ts, dl_mean, ul_mean, n, out_of_band_count}

On each smoothed sample (dl, ul):
  if no current_segment: open one at now with dl, ul
  elif |dl - dl_mean| <= band(dl_mean) AND |ul - ul_mean| <= band(ul_mean):
      update running means (Welford / cumulative), out_of_band_count = 0
  else:
      out_of_band_count += 1
      if out_of_band_count >= HYSTERESIS_TICKS:
          close current_segment at (now - HYSTERESIS_TICKS)  → write to DB
          open new segment starting at (now - HYSTERESIS_TICKS)
On disconnect / app quit:
  close current_segment at now, write to DB, close session row.
```
The band check applies to download AND upload independently — either one breaking
the band (with hysteresis) splits the segment.

## Connectivity detection
- Primary signal: total bytes counter unavailable OR default interface disappears.
- Practical v1 approach: `psutil.net_if_stats()` — active interface `isup`; plus a
  cheap reachability check is NOT required for v1 (interface-level is acceptable).
- Emit `session_started` / `session_ended` signals; segmenter resets between sessions.

## Pagination & filter queries (repository.py only)
- Page query: `SELECT ... WHERE <filters> ORDER BY start_ts DESC LIMIT :page_size OFFSET :offset`
- Count query for total pages: `SELECT COUNT(*) ... WHERE <filters>`
- Filters compile to a `start_ts`/`end_ts` overlap range in UTC:
  - date D            → [local D 00:00, D 23:59:59] → UTC range
  - date range D1–D2  → [D1 00:00, D2 23:59:59]
  - date + time T     → records whose range CONTAINS that instant
  - date + time range → records OVERLAPPING [T1, T2]
  Overlap condition: `start_ts <= :range_end AND end_ts >= :range_start`

## PDF export (export/pdf_report.py)
- Input: same filter object as the table + the resulting full record list (NOT just one page).
- Layout: highlighted header band (brand color background) containing:
  line 1: "Internet Speed Report" • line 2: user's full name • line 3: date/date-time range.
- Body: table with columns Date | Time Range | Download | Upload, repeated header per page,
  zebra rows, footer with page number and generated-at timestamp.
- Full name: macOS/Linux `pwd.getpwuid(os.getuid()).pw_gecos.split(',')[0]`,
  Windows fallback `ctypes GetUserNameExW`, final fallback `getpass.getuser()`.

## Data flow for quit
`QApplication.aboutToQuit` → CollectorService.stop() → segmenter.flush() (closes open
segment + session) → thread join (max 3s) → exit. This MUST be implemented; losing the
open segment on quit is a bug.

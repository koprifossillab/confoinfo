# Confoinfo conference file — instructions for an AI assistant

You are converting a conference program (PDF, web page, spreadsheet, …) into **one JSON file** that
Confoinfo (https://koprifossillab.github.io/confoinfo/) can open. The person will load the file on
the site's **Add a conference** page (`/confoinfo/import/`). It stays on their device.

Machine-readable schema: https://koprifossillab.github.io/confoinfo/confoinfo-1.schema.json

## Output rules

- Output **a single JSON object**, UTF-8, no comments, no trailing commas. Save it as `<slug>.json`.
- **Copy, do not invent.** Take titles, names, times and rooms exactly as the source has them. If a
  value is not in the source, leave the field out. Do not translate titles or names.
- All times are **local time at the venue**, 24-hour `HH:MM`. Dates are `YYYY-MM-DD`.
- If the program is long, include every day and every room — a partial file looks like a complete
  one to the person using it. If you must stop, say clearly what is missing.

## Shape

```json
{
  "format": "confoinfo/1",
  "conference": { … },
  "rooms":     [ … ],
  "sessions":  [ … ],
  "abstracts": [ … ],
  "talks":     [ … ]
}
```

### `conference` (required)

| field | required | meaning |
|---|---|---|
| `slug` | yes | Short id: lowercase letters, digits, hyphens, up to 40. E.g. `"agu2026"`. Must not be `search`, `plan`, `settings`, `import`, `local`, `static`. |
| `short_name` | yes | Short display name, e.g. `"AGU 2026"` |
| `name` | yes | Full name |
| `timezone` | yes | IANA name of the venue, e.g. `"Asia/Seoul"`, `"America/Chicago"` |
| `start_date`, `end_date` | recommended | `YYYY-MM-DD` |
| `venue` | | City / building |
| `url` | | Conference website |
| `language` | | Language of titles, BCP 47 (`"en"`, `"ko"`, `"zh-CN"`). Default `"en"` |
| `color` | | Header color `#rrggbb` |
| `lunch_at` | | Usual lunch time `HH:MM` (default `12:30`) — used to label gaps as Lunch or Break |
| `source` | | Where the data came from, e.g. `"Program book PDF v3, 2026-10-01"` |

### `rooms` — the order is the order of the room tabs

```json
{"name": "Hall A", "short": "A", "floor": "2F"}
```

`name` is required and unique. `short` is a short tab label. A talk may use a room not listed here;
it is added at the end with a warning, so list them all.

### `sessions` — the order is the order of the session list

```json
{"code": "T3", "group": "Oral sessions", "title": "Coastal processes",
 "conveners": "Jane Doe, Kim Min", "description": "Paragraph.\n\nParagraph.", "poster_count": 12}
```

`code` is required and unique (use the program's own session code; if there is none, make short
stable ones like `"S01"`). Sessions with the same `group` are listed under one heading.

### `abstracts` — optional, only if the source has abstracts or author lists

```json
{"key": "T3-01", "session": "T3", "title": "…", "text": "Abstract body.\n\nSecond paragraph.",
 "keywords": ["…"], "page": 37,
 "authors": [{"name": "Jane Doe", "affiliations": [1], "corresponding": true},
             {"name": "Kim Min", "affiliations": [1, 2]}],
 "affiliations": ["Univ. A, City", "Institute B, City"]}
```

`key` and `title` are required; `key` is unique among abstracts. `affiliations` numbers point into the
`affiliations` list, starting at 1. An abstract that no talk points to (a poster, an unscheduled one)
is still shown under its session.

### `talks` — everything with a time and a place

```json
{"key": "1103-hallA-0930", "date": "2026-11-03", "start": "09:30", "end": "09:45",
 "room": "Hall A", "session": "T3", "title": "…", "speaker": "Jane Doe",
 "kind": "talk", "abstract": "T3-01", "code": "O-12"}
```

| field | required | meaning |
|---|---|---|
| `key` | yes | Unique, **stable** id — see below |
| `date`, `start` | yes | `YYYY-MM-DD`, `HH:MM` |
| `title` | yes | |
| `end` | recommended | `HH:MM`. Without it the talk has no length |
| `room` | | A `rooms` name. Leave out (or `null`) for events for everyone (opening, plenary, banquet) |
| `session` | | A `sessions` code |
| `speaker` | | Presenter (usually the first author) |
| `kind` | | `talk` (default), `plenary`, `keynote`, `poster`, `break`, `event` |
| `abstract` | | An `abstracts` key — **must exist** |
| `code` | | Number the conference gives the talk (poster board, `O-12`) |

- **Breaks:** you do not need to write coffee breaks or lunch. Gaps of 10 minutes or more between
  talks in the same room are shown as Break / Lunch automatically. Write a `kind: "break"` entry only
  when the program names it (e.g. "Poster viewing & coffee").
- **Posters** with a time slot: one talk each with `kind: "poster"`, the poster session's time, and
  the board number in `code`.

## Keys must be stable

People bookmark talks, and a bookmark is tied to the talk's `key` (together with the conference
`slug`). If the person later loads a corrected file, bookmarks survive only for keys that did not
change. So **do not number rows** (`"1"`, `"2"`, …) — one inserted talk would shift every key after it.
Build keys from the talk itself, e.g. the program's own talk number (`"O-12"`) or
`date + room + start` (`"1103-hallA-0930"`). Never change the `slug` of a conference that was
already loaded.

## Errors that stop the file from loading

- `format` is not `"confoinfo/1"`; a required field is empty; bad `slug`
- `timezone` is not an IANA name
- a date that is not `YYYY-MM-DD`, a time that is not `HH:MM`
- two rooms with the same `name`, two sessions with the same `code`, two talks or two abstracts with
  the same `key`
- a talk whose `abstract` is not in `abstracts`; an unknown `kind`

Unknown `room` or `session` names only give a warning.

## Before you hand over the file, check

1. It parses as JSON.
2. Every day of the program is present, and the number of talks per day looks right.
3. Every `talk.room` is in `rooms`, every `talk.session` in `sessions`, every `talk.abstract` in `abstracts`.
4. Times are 24-hour and in the venue's time zone; `end` is after `start`.
5. Keys are unique and not row numbers.

## Minimal example

```json
{
  "format": "confoinfo/1",
  "conference": {"slug": "example2026", "short_name": "EX 2026", "name": "Example Meeting 2026",
                 "timezone": "Asia/Seoul", "start_date": "2026-11-03", "end_date": "2026-11-04",
                 "venue": "Busan"},
  "rooms": [{"name": "Hall A"}, {"name": "Hall B"}],
  "sessions": [{"code": "T1", "group": "Oral", "title": "Sediments", "conveners": "Jane Doe"}],
  "abstracts": [{"key": "T1-01", "session": "T1", "title": "Mud on the shelf",
                 "authors": [{"name": "Jane Doe", "corresponding": true}]}],
  "talks": [
    {"key": "opening", "date": "2026-11-03", "start": "09:00", "end": "09:30",
     "title": "Opening", "kind": "event"},
    {"key": "T1-01", "date": "2026-11-03", "start": "09:40", "end": "09:55", "room": "Hall A",
     "session": "T1", "title": "Mud on the shelf", "speaker": "Jane Doe", "abstract": "T1-01"}
  ]
}
```

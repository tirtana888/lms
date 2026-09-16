# SCORM in this deployment

How SCORM packages are stored, served and talked to here, and what to check when
a package misbehaves. Written after a production incident (2026-09-16) that took
a long time to diagnose because every symptom pointed away from the actual cause.

## Two independent paths

| | Chapter-level | Lesson-level |
| --- | --- | --- |
| Author sets it up in | `ChapterForm.vue` (whole chapter *is* the package) | Scorm block inside a lesson (`utils/scorm.js`) |
| Extracted to | `private/scorm/<course>/<chapter title>/` | `private/scorm-lesson/<course>/<lesson>/` |
| Served by | `SCORMRenderer` | `LessonSCORMRenderer` |
| URL | `/scorm/<course>/<title>/...` | `/scorm-lesson/<course>/<lesson>/...` |
| Player hosted in | `pages/SCORMChapter.vue` | `components/ScormBlock.vue` |

Both live in `lms/page_renderers.py`. They are separate classes on purpose —
`"scorm-lesson/"` is not a substring of `"scorm/"`, so neither `can_render()`
ever matches the other's paths.

## Every byte goes through Python, deliberately

`railway/nginx-app.conf` has **no** direct-disk rule for `/scorm`. That is not an
oversight: the Python permission gate (course access + drip/deadline locks) must
run for every file, otherwise the package is a way around the lock that never
touches `get_lesson`.

The cost is real and worth knowing: **one lesson is 100-120 separate requests**
(every JS chunk, font, image and content fragment is its own file). Two things
keep that affordable:

- `_serve_scorm_file()` serves through werkzeug's `send_file(conditional=True,
  max_age=3600)`, so repeat views get `304`s or never ask at all. Extracted files
  only change when an author re-uploads — hence the hour. The response is marked
  `private`: it is permission-gated, so no shared proxy may hold it.
- An *allowed* permission decision is cached 60s per `(user, course, lesson)`.
  Only the allow. A denial is always re-evaluated, and a lesson that locks
  mid-session closes within that window.

Before those two existed, a single lesson open queued 100+ requests through the
web pool and the tail latency climbed past a second.

## The SCORM API bridge — and why learner identity is not optional

Both hosts expose `window.API` (SCORM 1.2) and `window.API_1484_11` (2004). The
player, running inside the iframe, walks up `window.parent` to find them.

`getDataFromLMS(key)` answers a deliberately small set of keys. **One of them is
load-bearing in a way that is not obvious:**

```js
// The player's own bundle:
getUsername:  () => apiWrapper.doLMSGetValue("cmi.core.student_name")
getAccountId: () => apiWrapper.doLMSGetValue("cmi.core.student_id")
```

A package that *also* reports over xAPI builds every statement's **actor** from
those two. Answer `''` and the statement has an empty account, the LRS rejects
the whole batch with `400`, the player retries, gives up, and paints **its own**
full-screen "connection lost" over the lesson. To a student that reads as broken
internet — while the lesson content and our own progress saving were fine all
along.

So: **when adding keys here, remember some are read for identity, not just for
progress.** Answer both spellings — 1.2 packages ask `cmi.core.*`, 2004 asks
`cmi.*`.

`ScormBlock.vue` is mounted standalone by EditorJS and never receives pinia, so
the display name is passed in as a prop from `utils/scorm.js`, where the store
is available.

## Debugging a misbehaving package

**If the symptom leaves no trace in the server logs, stop looking at the server.**
That is the whole lesson of the incident above. Go to browser devtools first:
a failing request that never reaches us is invisible to every server-side tool,
and no amount of log reading will surface it.

1. **Browser devtools → Network.** Look at what is red or non-2xx. A `400` on
   `statements` is xAPI reporting; open its **Response** body, which names what
   is wrong. `save_progress` tells you whether our own SCORM bridge is working.
2. **Our access logs, with durations:** `railway logs --http --lines 500`. This
   is much better than the raw nginx text log — it carries per-request duration,
   which is how queueing shows up (a latency ramp inside one burst).
3. **Read the package itself.** It is on disk and greppable over SSH:
   `sites/<site>/private/scorm-lesson/<course>/<lesson>/`. Useful files:
   - `imsmanifest.xml` → `schemaversion` (1.2 vs 2004 4th Edition)
   - `publishSettings.js` → publish mode, module list, service endpoints
   - `lang/<locale>.json` → if an error message is in here, the screen is the
     **player's**, not ours and not the browser's
   - the player bundle under `static/js/` → what it reads and where it posts

`ps` and `free` are not installed in the container. Use `/proc/*/status` (match
against the *untruncated* cmdline) and `/sys/fs/cgroup/memory.current`.

## Known limitations

- `getDataFromLMS` still answers `''` for keys beyond status, suspend/launch data
  and identity (`cmi.core.entry`, `credit`, `score.*`, …). No package has needed
  them yet; another might.
- Re-uploading a package keeps the same URLs, so a learner who already loaded it
  can see the old files for up to an hour (`SCORM_ASSET_MAX_AGE`). Shorten that
  constant if content is revised often.
- Legacy packages extracted under `public/scorm` are served directly by nginx in
  production, bypassing the Python gate. They stay ungated until re-uploaded.

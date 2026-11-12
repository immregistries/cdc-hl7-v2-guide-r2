# Review comments

Reviewers comment on the draft through [InteropHub](https://informatics.immregistries.org/hub), on topic
52, "CDC HL7 v2 Guide (Release 2)". Comments are stored in InteropHub, not in this repository.

## How it works

- **One document key for the whole site:** `cdc-hl7-v2-guide-r2`, registered to topic 52.
- **Comments attach to a page.** Each section (card) is a review anchor: its card ID, for example
  `administering-organization-rxa-11`. A comment can also say what on the page it is about: the whole
  section, one conformance statement, or a figure. This is stored as the block index (0 = whole section;
  `n` = statement `sn`; `900 + k` = the k-th figure), with the statement text or figure caption as the snippet.
- **Generated pages have anchors too:** `structure` (chapter 7), `structure-z22` (profile),
  `structure-seg-rxa` (segment), `structure-flavor-<flavor>`, `structure-dt-<type>`,
  `structure-vs-<value-set>`, `structure-cocon-z22`, `quality`, `quality-igamt` (where a comment can be
  about one reviewed finding), `glossary`, and `resources`.
- **Sign-in** uses the InteropHub sign-in shared by AIRA guides (PKCE, app `topic-reference`). One sign-in
  covers every page. Reading comments also requires sign-in.
- **Authors** (people who can edit topic 52) can record a disposition (Persuasive, Not Persuasive, and so
  on) with a change note, and close or reopen threads, on the page or in InteropHub.
- **Links from InteropHub** go to the site's home page (`?interophub=signin#comment-<id>` or `#<anchor>`),
  which forwards to the right page.
- The navigation tree shows a 💬 count on sections that have comment threads (blue while any are open).

The client is `site/theme/comments.js`. It uses the InteropHub guide API (`/api/guide/{documentKey}`) and
has no dependencies.

## Registering the guide (once, by a topic 52 editor)

1. In InteropHub, open topic 52 and go to **Guide** (`/hub/es/topic-guide/52`).
2. Document key `cdc-hl7-v2-guide-r2`; title "CDC HL7 v2 Guide (Release 2) – draft"; repository
   `https://github.com/immregistries/cdc-hl7-v2-guide-r2`; hosting **External**.
3. URL: label "Draft (main)", URL `https://immregistries.github.io/cdc-hl7-v2-guide-r2/main/`. This is
   under the approved prefix `https://immregistries.github.io/`. Sign-in and the API accept every page
   under it.
4. Save, then set `comments.enabled: true` in `data/guide.yml` and push.

Topic 52 is in a public Topic Space, which matches a publicly published guide.

## Testing against a local InteropHub

Register the same document key in a local InteropHub with the URL `http://localhost:8765/`, then:

```powershell
$env:GUIDE_COMMENTS_HUB = "http://localhost:8080/hub"
python tools/build_site.py
python -m http.server 8765 --bind 127.0.0.1 --directory output/site
```

Open `http://localhost:8765/` (use `localhost`, not `127.0.0.1`, so it matches the registered URL).

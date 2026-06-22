# TODO

A tiny **boards › lists › tasks** todo app in a single file: pure HTML/CSS/JS, state in `localStorage`. No server, no build, no dependencies.

**Live:** https://todo.surf

![TODO — light](docs/screenshot-light.png)

## Try it

Open [`index.html`](index.html) in a browser, or visit the [live page](https://todo.surf). Everything is saved in your browser's `localStorage` — it never leaves your machine (and so does not sync across devices).

## Quick guide

Everything runs from the **toolbar**. Click a board name, list name, or task to **select** it (blue outline); the toolbar then acts on that selection. Click empty space to deselect.

| Button | Action |
|:------:|--------|
| ↺ / ↻ | **Undo / Redo** — up to 10 steps |
| **+** | **Add** — a task under the selected list, a list under the selected board, or a new board when nothing is selected |
| ↑ / ↓ | **Move** the selection up or down |
| ✎ | **Edit** the selection inline (type, `Enter` to save, `Esc` to cancel) |
| ⧉ | **Duplicate** the selection in place (current board if nothing is selected) |
| 📋 | **Copy to clipboard** — the selected board/list/task as **markdown** (current board if nothing is selected) |
| 🗑 | **Delete** the selection — disabled until you select a board, list, or task |
| 📥 / 📤 | **Import / Export** — merge a JSON file into your boards, or download everything as `todo.json` |

**Import / export.** Export downloads your whole tree as `todo.json`. Import reads a file of the same shape — `{ board: { list: [ {text, done} ] } }` — and *merges* it in: new boards and lists are added, and tasks are appended to existing lists unless a task with that text is already there (so re-importing the same file is safe). A `todos.json` from the command-line version drops straight in.

More:

- **Toggle done** — click a task's checkbox.
- **Reorder** — drag the ⠿ grip on a task or list (or drag a board pill) — works with mouse or touch.
- **Switch board** — click a board pill.
- **Inline add/edit shortcut** — committing an *empty* field deletes the item (a quick way to remove the thing you're editing).
- **Light / dark** — the ◑ button by the title; your choice is remembered.
- **Install it** — in Chrome/Edge an **Install app** button appears by the title; once installed it opens in its own window and works offline. After a new deploy a **New version — refresh** prompt appears at the bottom of the page.
- **Sync across devices (optional)** — the ☁ button by the title syncs your boards through your own Google Drive (a hidden, app-private file — it can't see the rest of your Drive). It needs the one-time setup below; until then it's inert.

![TODO — dark](docs/screenshot-dark.png)

## Google Drive sync setup

Sync runs entirely in the browser — no server. It needs an OAuth client ID from a Google Cloud project. For personal use the app stays in **Testing** mode (no Google verification needed); only Google accounts you whitelist can connect.

1. In the [Google Cloud Console](https://console.cloud.google.com/) create (or pick) a project.
2. **APIs & Services → Library →** enable **Google Drive API**.
3. **APIs & Services → OAuth consent screen:** User type **External**, fill in the app name/email, add the `.../auth/drive.appdata` scope, and under **Test users** add every Gmail address that should be able to sync. Leave publishing status on **Testing**.
4. **APIs & Services → Credentials → Create credentials → OAuth client ID → Web application.** Under **Authorized JavaScript origins** add `https://todo.surf` (and `http://localhost:PORT` if you test locally). Copy the **Client ID**.
5. Paste it into `index.html` as `DRIVE_CLIENT_ID`, then bump the `CACHE` string in `sw.js` and deploy.

Then click ☁, sign in once, and your boards sync. Conflict resolution is last-write-wins by an edit timestamp — fine for one person across devices; simultaneous edits on two devices keep whichever saved last.

## How it works

The data is one ordered tree: `{ board: { list: [ {text, done}, … ] } }`, kept in `localStorage`. Every change records a whole-document snapshot for undo/redo — simple and always correct for data this small.

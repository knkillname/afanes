# ⚠️ Troubleshooting

These are the failures a user is most likely to see, and the shortest path through each one.

:::{admonition} tl;dr
:class: note

Most problems come from a missing interface runtime, a browser session that lost its Python process, a
note whose frontmatter cannot be parsed, a vault without a valid `afanes.yaml`, or an external program
changing a file during an edit.
:::

## 🔌 The desktop window does not start

Afanes reports the missing runtime and exits instead of switching presentations silently. Recreate
the environment from the source checkout:

```console
hatch env create
hatch run afanes
```

If the native window still cannot start, run `hatch run afanes --web` to use the browser presentation.
The app never downloads a runtime while starting.

## 🌐 A browser tab shows "Working…"

The tab has lost its Python session, usually because the server process exited. Start the server again
and reload the tab. Closing a tab releases its session, so Afanes can be reopened in a new one.

Only one browser session can drive the workspace at a time. A second tab shows a notice until the first
one closes.

## 📄 A note opens in raw rescue mode

The frontmatter cannot be parsed. Raw rescue mode shows the complete file text and hides the labels.
Saving writes exactly what you typed; once the text parses, the normal editor returns. Unreadable notes
are listed in the browser's **Unreadable notes** section.

Check for an unclosed `---` fence, an unknown `type`, a retired key, or a value that is not valid YAML.
See [Frontmatter](frontmatter.md) and [Migration](migration.md).

## 🧷 A link is unresolved

No page with that name exists in the reference's scheme. The note may have been renamed, moved to
`trash/`, or deleted by another program. Restore the file or create a page with that name; Afanes does
not retarget the link automatically.

Use the [Names and links](names-and-links.md) rules to check the scheme and matching behavior.

## ⚔️ A save conflict appears

Another program changed the file after Afanes read it. The save stops and the page offers to reload the
file or overwrite it with your version. If the file was moved or deleted, the page offers to recreate it
or discard the draft.

:::{warning}
Overwriting a conflict discards the other program's edit to that file. Reload when the other edit is the
one you want to keep.
:::

## 🗂️ A vault opens but looks incomplete

Notes under `trash/` are excluded from scans, name uniqueness, and reference resolution. A note under
`inbox/` appears only under **Inbox**; a `type: note` outside `inbox/` appears under **Needs attention**.
Unreadable notes appear only in their own group. Folders are conventions, so a note is still in the
vault even when its folder is unusual.

## ⚙️ A folder is refused as a vault

Afanes accepts a folder only when its root contains a valid `afanes.yaml` settings file. The current
contents are exactly:

```yaml
schema_version: 1
```

- **The folder has no settings file.** If it is writable and has all five default folders (`inbox/`,
  `trash/`, `reference/`, `projects/`, and `log/`), Afanes offers adoption. Confirm the offer, or run
  `afanes vault adopt DIR`. Adoption writes only `afanes.yaml`. A folder missing a default folder or
  without write access cannot be adopted.
- **The settings file is invalid.** Extra keys, malformed YAML, a missing or non-integer
  `schema_version`, and duplicate keys are refused. The file is left byte for byte unchanged. Fix it by
  hand to contain only `schema_version: 1`, or restore a copy from a backup.
- **The schema is newer or older.** This version of Afanes supports schema `1`. A newer file asks you
  to update Afanes. An older schema is refused before 1.0 rather than migrated.
- **The vault is read-only.** A valid versioned vault opens for browsing even when it cannot be
  written. An unversioned read-only folder cannot be adopted because the settings file cannot be
  created; add `afanes.yaml` from a writable copy.

Afanes never repairs, rewrites, deletes, or guesses at a settings file it cannot validate.

## 🧭 See also

- [Pages and editing](../guide/pages-and-editing.md)
- [Browser mode](../guide/browser-mode.md)
- [Command line](../guide/command-line.md)

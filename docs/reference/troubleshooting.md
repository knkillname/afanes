# ⚠️ Troubleshooting

These are the failures a user is most likely to see, and the shortest path through each one.

:::{admonition} tl;dr
:class: note

Most problems come from a missing interface runtime, a browser session that lost its Python process, a
note whose frontmatter cannot be parsed, or an external program changing a file during an edit.
:::

## 🔌 The desktop window does not start

Afanes reports the missing runtime and exits instead of switching presentations silently. Install the
desktop runtime:

```console
pip install "afanes[desktop]"
```

If the native window still cannot start, run `afanes --web` to use the browser presentation. The app
never downloads a runtime while starting.

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

## 🧭 See also

- [Pages and editing](../guide/pages-and-editing.md)
- [Browser mode](../guide/browser-mode.md)
- [Command line](../guide/command-line.md)

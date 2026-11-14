# ✅ Review

Review is the guided pass over work that needs attention. At launch, Afanes shows a digest when one or
more own steps are due or overdue, or when a reminder is due. The digest reports the count in neutral
items, writes nothing, and starts the guided review when activated.

:::{admonition} tl;dr
:class: note

Review counts due reminders, pending captures, due steps, waiting steps, and open projects without a
next step. It never classifies or changes anything without an explicit choice.
:::

```{image} ../_static/screenshots/review.png
:alt: A review card for a due step with do it now, postpone, delegate, open project, and skip actions
:class: screenshot
```

## 🔔 The digest and the badge

The **Review** entry shows how many items need attention: due reminders, pending Inbox captures, due
or overdue own steps, waiting steps, and open projects with no open step. Healthy open projects do not
contribute to the badge. Selecting Review with zero pending items shows the zero state and starts no
session.

While a vault is open, the badge is recomputed from the current scan every five seconds. A reminder
that becomes due updates the count without a manual refresh; it does not join an active session and
waits for the next one. The refresh reads the snapshot only and writes nothing.

## ⏰ Due reminders

A due reminder leads the queue, before Inbox captures. When several reminders are due, the one whose
latest occurrence is oldest comes first. The card shows the note title and a relative time such as
**2 hours ago**; the exact cadence, times, and zone live on the note page. See
[Frontmatter](../reference/frontmatter.md) for the reminder key.

A reminder card offers:

- **Open Page**: opens the note and leaves the reminder due;
- **Dismiss**: records the occurrence in `handled`, preserves the note body, status, and schedule, and
  advances;
- **Skip**: changes nothing.

A reminder pauses while its note is in Trash or its status is `done`, `cancelled`, `archived`, or
`later`. `waiting`, an absent status, and an active log entry keep it eligible. When a paused note
returns, the next session shows one catch-up entry for the latest missed occurrence. Afanes does not
create operating-system notifications; the badge and the digest are the signals.

## 🧾 Queue order

Starting a review snapshots a queue in this order:

1. Due reminders, most overdue first.
2. Pending Inbox captures.
3. Due or overdue own steps.
4. Waiting steps.
5. Open projects with no open step.
6. Healthy open projects, for a quick confirmation.

Closed projects are excluded. The browser shows the session's snapshot queue as cards in order and
marks the current card; selecting a card makes that item current in the detail, without reviewing or
skipping anything. The detail region keeps the current card and its actions. Notes created during a
session, and reminders that become due, do not join the queue and wait for the next review session.
The session is not saved across restarts; the pending count is recomputed from the vault.

## 🎛️ Card actions

An Inbox item opens the existing Processing Wizard. Confirming an outcome applies it and advances the
session; cancelling leaves the capture in the Inbox. The review never chooses an outcome or metadata
from the capture text.

A due step card offers:

- **Do It Now**: checks the step and records `actual`;
- **Postpone…**: replaces `plan`;
- **Delegate…**: adds an owner and moves the step to waiting;
- **Open Project**: shows the project page;
- **Skip**: changes nothing.

A waiting step card shows its owners and offers **Reassign…**, **Open Project**, and **Skip**. Reassign
replaces the owners.

A project card shows the project title, status, optional due date, its next step, and any other open
steps. **Open Project** opens the page. For a project with no open step, the card offers adding a next
step, marking the project done, deferring it to `later`, or skipping. Adding a step requires text and
appends a task-list item to the project body. Marking done and deferring both require confirmation. A
failed card write is reported in a toast; the inline step and project forms keep their own error text.

Step text in every review card is rendered Markdown, so links and emphasis appear the same way they do
on the project page. Raw Markdown source appears only in edit mode. A link label inside a card is
display-only; opening the project remains an explicit action.

:::{warning}
**Skip** leaves the project or step exactly as it was, so it remains in the next session's pending
count. Skipping is not a way to clear an item permanently.
:::

## 🏁 Finishing a session

After the last item, the session reports how many items were reviewed and skipped and returns to the
browser. Review never classifies captures, changes a project status, checks a step, or creates a note
without an explicit choice.

## 🧭 See also

- [Processing](processing.md)
- [Inbox](inbox.md)
- [Projects and steps](projects-and-steps.md)

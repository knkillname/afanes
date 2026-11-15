# 📅 Dates

:::{admonition} tl;dr
:class: note

Every date field has a calendar action. The picker is Monday-localized and keyboard accessible, and
it writes an ISO value through the field's existing save path.
:::

Every date field carries a calendar action in its suffix, and the read-mode date actions use the same
calendar. The fields keep ISO text (`YYYY`, `YYYY-MM`, or `YYYY-MM-DD`), so typing remains a complete
alternative to the picker.

## 🗓️ Choosing a date

Open the calendar action to see the current value, the selected caption, and a Monday-first month
grid. A day click selects that day; **Select** writes it. **Cancel**, Esc, and a click outside the
dialog discard the pending value without writing anything.

The Page Date field accepts three precisions:

| Mode | Writes | Use |
| --- | --- | --- |
| **Day** | `YYYY-MM-DD` | A dated note, log entry, or day-specific value |
| **Month** | `YYYY-MM` | A note or log entry that names a whole month |
| **Year** | `YYYY` | A note or log entry that names a whole year |

Other date fields offer Day only: the project due date, a step plan date, the Processing due date,
the Review postpone date, and the reminder one-shot date. The reminder time stays typed in its own
field.

Switching modes keeps the day-of-month. Choosing a new month or year clamps that day to the month
length, so 31 January becomes the last day of February and 29 February becomes 28 February in a
common year.

## ⌨️ Keyboard

| Key | Day mode | Month mode | Year mode |
| --- | --- | --- | --- |
| Arrows | One day or one week | One month or one row | One year or one row |
| Page Up / Page Down | One month | One year | One decade |
| Shift + Page Up / Page Down | One year | — | — |
| Home / End | Start or end of the week | January or December | Start or end of the page |
| Enter | Confirm a focused day | Confirm a focused month | Confirm a focused year |
| Esc | Cancel | Cancel | Cancel |

## 🌍 Language

Month names, weekday labels, the selected caption, the mode switch, and the period action follow the
active language. The calendar starts on Monday in both English and Spanish, and the date written to
the vault does not depend on the interface language.

Dates outside 1900–2100 are selectable. The picker reads and writes the full calendar range.

## 💾 When a date is saved

The picker only supplies a value. The field runs its existing save command afterwards. For a log
entry, changing the Date field still renames and moves the file and updates generated headings; a
custom heading is preserved.

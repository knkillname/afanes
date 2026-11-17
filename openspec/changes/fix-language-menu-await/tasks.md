# Tasks

## 1. Restore the language menu

- [x] 1.1 In `src/afanes/ui/components/language.py`, make `_choose_english`, `_choose_spanish`, and `_choose_system` coroutine functions that await `self.on_select(...)`, and require `Callable[[str | None], Awaitable[None]]` without the `| None` return. Update the matching `on_language` annotations in `src/afanes/ui/views/inbox.py` and `src/afanes/ui/views/workspace.py`. Verify `hatch check` passes and a scratch script constructs `LanguageMenu` and reports `inspect.iscoroutinefunction` as true for all three `on_click` handlers.
- [x] 1.2 Fix the regression test in `tests/ui/test_app.py`: keep the Spanish preference-write scenario, add English and system cases, and assert that every language item's `on_click` is a coroutine function. Verify `hatch test tests/ui/test_app.py -k "language"` passes and that reverting the handlers to sync makes the new assertion fail.
- [x] 1.3 Add one `Unreleased` → `Fixed` entry to `CHANGELOG.md` naming `fix-language-menu-await`, the inert language menu, and the Flet dispatch rule; record `README: no change required` and `Docs: no change required`. Verify `hatch version` still reports `0.14.0`, `git diff CHANGELOG.md` shows only the new entry, and the entry names the defect.
- [x] 1.4 Run `hatch check`, `hatch test --cover`, `openspec validate --all --strict`, `openspec doctor`, and both vocabulary greps from `AGENTS.md` section 6.1. Verify every command passes and coverage stays at or above 85%.

## 2. Packaged verification

- [x] 2.1 With maintainer approval, push the fix to `main` and dispatch `release.yml` as a dry run. Download the new `afanes-release` artifact, verify its checksums, extract the bundle, and run it: choose **English**, confirm the restart toast, confirm `~/.config/afanes/settings.json` gains `"language": "en"`, restart and confirm the interface starts in English, then choose **System Language** and confirm the key clears. Verify the run is green, the publish job is skipped, and no release is created.
- [x] 2.2 Record the packaged run URL and result for the language row, then report the new artifact to the `automate-release-publishing` change. Verify the language row can be marked green and that the release change still requires the full packaged gate on the final `1.0.0` artifact, because this fix changes interface code after the earlier pass.

## Verification record

- Dry run `44015988044` on `8de4fb9`: green, the publish job was skipped, and no release was created. The `afanes-release` artifact checksums verified.
- On the extracted bundle, **English** wrote `{"version": 1, "language": "en"}` and the relaunch started in English; **System Language** wrote `{"version": 1, "language": null}` and the relaunch returned to the system Spanish locale. The running session kept its language until each restart.
- No "never awaited" warning appears in any packaged run of the fixed build.

## Workflow follow-up

- Archive this change after review. It restores an existing requirement, so it sets `skip_specs: true`, keeps its entry under `Unreleased`, and does not bump the version, tag, or publish.
- Commit the archive with a subject that names the restored behavior and a body line `Archived OpenSpec change: fix-language-menu-await`.
- Resume `automate-release-publishing` at task 4.1 with the new artifact; never reuse the pre-fix gate results as the final `1.0.0` evidence.

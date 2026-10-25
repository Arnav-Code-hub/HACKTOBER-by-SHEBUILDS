## What changed

<!-- One or two sentences. The PR title becomes the commit message on main
     (we squash-merge), so make it a Conventional Commit:
     feat(api): cluster demands by geo proximity -->

## Why

<!-- The problem this solves. Link the issue if there is one. -->

## How it was tested

<!-- Commands you ran, or the journey you clicked through. "CI is green" is not
     a test plan — CI proves nothing broke, not that this works. -->

## Screenshots / recordings

<!-- Required for any user-visible change. Web: light and dark. Mobile: the device. -->

---

- [ ] Under ~400 lines changed (a bigger PR gets rubber-stamped, which is the same as no review)
- [ ] `make check` passes locally
- [ ] **Schema change?** migration included, and it applies to an empty database
- [ ] **API change?** `make contracts` run and the generated output committed
- [ ] **Prompt change?** eval scores before/after pasted below
- [ ] **New env var?** added to the relevant `.env.example` with a comment
- [ ] No secrets, keys, tokens or real citizen data in the diff

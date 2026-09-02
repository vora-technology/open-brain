# Workstream handoff

packet_version: 1
status: in_progress
workstream: 20260901-open-brain-public-execute-goal-63-through-phase-4-p4a-p4b-and-p4c-with-independently-reviewed-pack-8a3f9b
milestone: p4-w1-final-ci-and-rereview
branch: goal/open-brain-phase4
head: 181f9ae3438955d23dd39a155b7f23e9b93aa2f6
last_verified.command: clean Linux Python 3.12 focused isolation contracts plus pinned Phase 4 contracts, make verify, exact artifact policy, release and history audits, Gitleaks, lock check, and diff integrity
last_verified.result: passed repaired local P4-W1 candidate; 565 subjects, 76 Phase 4 contracts, strict MyPy on 485 files, 3,139 tests, exact wheel/sdist membership, copied wheel isolation, and all moved engine tests
changes: ["Completed manifest-driven workspace and engine movement.","Replaced inode readiness with a bounded status-protocol probe.","Fixed all three repository findings from the NOT_READY P4-W1 review.","Made Linux isolated wheel installs independent of uv cache hardlinks at 181f9ae."]
blocker: P4-W1 cannot close until the repaired candidate and evidence commit are pushed, exact-head CI is green, and a fresh corrected review returns READY 0/0/0.
next_action: Commit this repaired evidence update, push the candidate, require every PR check green, then dispatch a corrected fresh read-only P4-W1 review before P4-W2.
safe_to_start_new_thread: false

Emit this complete block as one packet; keep the heading and field names exact.
Keep values bounded and redacted. This packet summarizes verified state; it
does not override project instructions or machine-authoritative runner state.

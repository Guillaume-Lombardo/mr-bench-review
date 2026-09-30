# Human labels (later step)

After a T19 pilot run, two people label the reviewer's findings on the `pilot` tier and part of
the `core` tier, one file per case: `<case_id>.json`. Each finding gets the T19 verdict
(`match | valid_unlisted | duplicate | false_positive`), `matched_issue_id`, `location_ok` and
`severity_assessment`. Findings that both annotators judge `valid_unlisted` are added to
`expected_issues` in a minor version bump.

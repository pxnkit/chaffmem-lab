# Fixture audit

The JSON fixture contains original synthetic records created for local defensive testing
with coding-assistant support. No external corpus, private information, or product data is
included.

Each scenario has one synthetic critical scheduling record and four ordinary background
records. Background records contain no agent instructions, executable content, credentials,
false corrections, or requests to modify the target. Healthcare records are limited to
facility and appointment logistics and provide no diagnosis or treatment guidance.

When adding a record, keep the language factual and neutral, preserve a stable identifier,
record its origin label, and update the audit metadata before using it in an experiment.

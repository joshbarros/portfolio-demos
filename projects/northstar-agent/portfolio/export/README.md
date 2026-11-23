# Export

`northstar-agent-package.zip` is generated locally and intentionally not committed: it duplicates the
files in this folder. Rebuild it with:

```bash
cd projects/northstar-agent/portfolio
zip -qr export/northstar-agent-package.zip \
  TITLE.txt ROLE.txt DESCRIPTION.txt SKILLS.txt CHARACTER_COUNTS.json \
  PROJECT_STORY.md PROPOSAL_NOTES.md VIDEO_SCRIPT.md EVIDENCE.md CHECKLIST.md \
  screenshots video diagrams
```

The ZIP contains no `.env`, token, database dump or Upwork data.

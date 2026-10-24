# Data dictionary used in the model

The source file contains more fields. The model intentionally uses only the following non-identifying categorical fields:

| Field | Meaning used in this project |
|---|---|
| `stream` | A/L stream, for example Arts, Commerce or Physical Science |
| `syllabus` | New or old syllabus |
| `sub1`, `sub2`, `sub3` | The three selected A/L subjects |
| `sub1_r`, `sub2_r`, `sub3_r` | Grade letter for each selected subject |
| `ge_r` | General English grade; converted into the target |

Target rule:

- `Pass`: `ge_r` is A, B, C or S.
- `Non-pass`: `ge_r` is F, Absent or Withheld.

Privacy choices:

- `index`, rank columns, birth day/month/year and `gender` are excluded.
- The model is not intended to identify or rank individual students.

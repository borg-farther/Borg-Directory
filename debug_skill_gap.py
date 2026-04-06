#!/usr/bin/env python
from borg.dojo.skill_gap_detector import detect_skill_gaps

# Test what patterns match
user_messages = [
    ("Please parse this csv file", "sess_1"),
    ("Can you parse another csv file", "sess_2"),
    ("I need csv parsing help", "sess_3"),
]

gaps = detect_skill_gaps(user_messages)
print("Gaps found:", [(g.capability, g.request_count) for g in gaps])

# Test with parse csv explicitly
user_messages2 = [
    ("parse csv file", "sess_1"),
    ("parse csv data", "sess_2"),
    ("parse csv info", "sess_3"),
]
gaps2 = detect_skill_gaps(user_messages2)
print("Gaps2 found:", [(g.capability, g.request_count) for g in gaps2])

# What about just 'csv'?
user_messages3 = [
    ("csv parsing", "sess_1"),
    ("csv file", "sess_2"),
    ("csv data", "sess_3"),
]
gaps3 = detect_skill_gaps(user_messages3)
print("Gaps3 found:", [(g.capability, g.request_count) for g in gaps3])

"""
Synthetic data generator for the Edtech dbt portfolio project.

PORTFOLIO PROJECT, SYNTHETIC DATA. Every row here is made up. The structure mirrors the kind of
systems a B2B edtech company runs for university clients (a student information system, an LMS,
and payments), including the messiness that makes reconciliation hard. No real company or student data.

Run from the project folder:   python scripts/generate_data.py
It writes 5 CSV files into seeds/ (same output every time, thanks to a fixed random seed).
"""
import csv, os, random
from datetime import date, timedelta

random.seed(42)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "seeds")
os.makedirs(OUT, exist_ok=True)

TERMS = [  # term_code, start, end
    ("2024FA", date(2024, 9, 2), date(2024, 12, 13)),
    ("2025SP", date(2025, 1, 13), date(2025, 5, 2)),
    ("2025FA", date(2025, 9, 1), date(2025, 12, 12)),
    ("2026SP", date(2026, 1, 12), date(2026, 5, 1)),
]
UNIVERSITIES = [  # fictional names
    ("U01", "Harbor Point University", "WA", "HPU", 48000),
    ("U02", "Redcliff State University", "TX", "RSU", 62000),
    ("U03", "Northfield College", "GA", "NFC", 35000),
    ("U04", "Silver Lake University", "CA", "SLU", 55000),
    ("U05", "Eastbrook Institute", "NY", "EBI", 40000),
]
PROGRAMS = ["Business Analytics", "Computer Science", "Nursing", "Accounting", "Marketing", "Data Science"]
PROGRAM_TYPOS = {"Business Analytics": "Bus. Analytics", "Computer Science": "Comp Sci", "Data Science": "data science"}
FIRST = ["Ada", "Tunde", "Maria", "Chen", "Aisha", "Liam", "Priya", "Kwame", "Sofia", "Daniel", "Grace", "Omar",
         "Hana", "Lucas", "Zara", "Ethan", "Ngozi", "Mateo", "Leah", "Ibrahim", "Chloe", "Ravi", "Amara", "Noah"]
LAST = ["Okafor", "Smith", "Garcia", "Wang", "Bello", "Johnson", "Patel", "Mensah", "Rossi", "Kim", "Adeyemi",
        "Brown", "Nguyen", "Silva", "Ali", "Martin", "Eze", "Lopez", "Cohen", "Khan", "Davis", "Owusu"]

def rdate(a, b):
    return a + timedelta(days=random.randint(0, (b - a).days))

def write(name, header, rows):
    with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)
    print(f"{name}: {len(rows):,} rows")

# 1) Universities (the B2B clients)
write("raw_universities.csv",
      ["university_id", "university_name", "state", "university_code", "annual_contract_usd", "contract_start", "renewal_date"],
      [(u, n, s, c, v, "2024-07-01", "2026-06-30") for u, n, s, c, v in UNIVERSITIES])

# 2) SIS students: one row per student registration per term (a student can continue into later terms)
sis, students = [], []
sid = 100000
for u, _, _, code, _ in UNIVERSITIES:
    for _ in range(random.randint(220, 340)):
        sid += 1
        fn, ln = random.choice(FIRST), random.choice(LAST)
        email = f"{fn}.{ln}{sid % 1000}@{code.lower()}.edu".lower()
        program = random.choice(PROGRAMS)
        first_term = random.randint(0, 2)
        students.append(dict(sid=sid, u=u, code=code, fn=fn, ln=ln, email=email, program=program, first_term=first_term))
        retained = True
        for t in range(first_term, len(TERMS)):
            if not retained:
                break
            term, start, end = TERMS[t]
            status = random.choices(["registered", "admitted", "withdrawn"], [0.12, 0.83, 0.05])[0]
            tuition = random.choice([2400, 3000, 3600, 4200])
            prog = PROGRAM_TYPOS.get(program, program) if random.random() < 0.06 else program   # messy spelling
            em = email.upper() if random.random() < 0.04 else (" " + email if random.random() < 0.02 else email)  # messy case/space
            sis.append([sid, u, fn, ln, em, prog, term, rdate(start - timedelta(days=60), start - timedelta(days=5)), status, tuition])
            retained = status != "withdrawn" and random.random() < 0.82
# exact duplicate rows (a classic SIS export problem)
for row in random.sample(sis, k=int(len(sis) * 0.02)):
    sis.append(list(row))
random.shuffle(sis)
write("raw_sis_registrations.csv",
      ["sis_student_id", "university_id", "first_name", "last_name", "email", "program", "term_code",
       "registration_date", "admission_status", "tuition_due_usd"], sis)

# 3) LMS users: different IDs, sometimes different emails; some students never get an account; some test accounts
lms, lms_map = [], {}
lid = 0
for s in students:
    if random.random() < 0.05:          # ~5% of students never get an LMS account
        continue
    lid += 1
    email = s["email"]
    r = random.random()
    if r < 0.07:   # personal email instead of school email
        email = f"{s['fn'].lower()}{s['ln'].lower()}{random.randint(1, 99)}@gmail.com"
    elif r < 0.10:  # alias at a different school domain format
        email = email.replace(".edu", ".student.edu")
    lms_map[s["sid"]] = f"L{lid:06d}"
    lms.append([f"L{lid:06d}", email, f"{s['fn']} {s['ln']}", s["code"], TERMS[s["first_term"]][1] - timedelta(days=random.randint(1, 10))])
for i in range(25):                     # internal / test accounts with no SIS student
    lid += 1
    lms.append([f"L{lid:06d}", f"test.user{i}@{random.choice(UNIVERSITIES)[3].lower()}.edu", f"Test User {i}", random.choice(UNIVERSITIES)[3], date(2024, 8, 15)])
write("raw_lms_users.csv", ["lms_user_id", "email", "full_name", "university_code", "created_date"], lms)

# 4) LMS weekly activity
act = []
enrolled = {(r[0], r[6]) for r in sis if r[8] == "admitted"}
for (sid_, term) in sorted(enrolled):
    if sid_ not in lms_map:
        continue
    _, start, end = next(t for t in TERMS if t[0] == term)
    engagement = random.choice([0.2, 0.5, 0.8, 1.0])
    wk = start
    while wk <= end:
        if random.random() < 0.85 * engagement + 0.1:
            act.append([lms_map[sid_], wk, random.randint(1, 12), random.randint(0, 4), random.randint(15, 600)])
        wk += timedelta(days=7)
write("raw_lms_weekly_activity.csv", ["lms_user_id", "week_start", "logins", "assignments_submitted", "minutes_active"], act)

# 5) Payments: full, partial, failed, refunds (negative), and a few orphans with unknown student ids
pay, pid = [], 0
for r in sis:
    sid_, term, status, due = r[0], r[6], r[8], r[9]
    if status == "withdrawn":
        continue
    _, start, _ = next(t for t in TERMS if t[0] == term)
    plan = random.choices(["full", "partial", "none"], [0.72, 0.2, 0.08])[0]
    if plan == "none":
        continue
    parts = [due] if plan == "full" else [round(due * random.choice([0.25, 0.5]), 2)]
    for amt in parts:
        pid += 1
        st = random.choices(["completed", "failed"], [0.95, 0.05])[0]
        pay.append([f"P{pid:07d}", sid_, term, rdate(start - timedelta(days=30), start + timedelta(days=45)), amt,
                    random.choice(["card", "bank_transfer", "sponsor"]), st])
    if random.random() < 0.02:          # refund
        pid += 1
        pay.append([f"P{pid:07d}", sid_, term, rdate(start + timedelta(days=10), start + timedelta(days=60)), -round(due * 0.25, 2), "card", "refunded"])
for _ in range(12):                     # orphan payments (student id not in SIS)
    pid += 1
    pay.append([f"P{pid:07d}", random.randint(900000, 999999), random.choice(TERMS)[0], date(2025, 2, 1), 500, "bank_transfer", "completed"])
write("raw_payments.csv", ["payment_id", "sis_student_id", "term_code", "payment_date", "amount_usd", "payment_method", "payment_status"], pay)
print("Done. PORTFOLIO PROJECT, SYNTHETIC DATA.")

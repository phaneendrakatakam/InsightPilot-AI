from __future__ import annotations
from pathlib import Path
from datetime import date, datetime, timedelta
import csv
import random

SEED = 20260908
random.seed(SEED)

ROOT = Path(__file__).resolve().parent
START_DATE = date(2026, 1, 1)
END_DATE = date(2026, 8, 31)

REGIONS = [
    (1, "NORTH", "North"),
    (2, "SOUTH", "South"),
    (3, "EAST", "East"),
    (4, "WEST", "West"),
]

PLANS = {"FREE": 0.0, "BASIC": 999.0, "PRO": 2499.0, "ENTERPRISE": 9999.0}

PRODUCTS = [
    (1, "PRD001", "Analytics Add-on", "ADD_ON", 1499.0, "ACTIVE"),
    (2, "PRD002", "Automation Pack", "ADD_ON", 1999.0, "ACTIVE"),
    (3, "PRD003", "Priority Support", "SERVICE", 2999.0, "ACTIVE"),
    (4, "PRD004", "Data Export Pack", "ADD_ON", 999.0, "ACTIVE"),
    (5, "PRD005", "Audit Toolkit", "ADD_ON", 2499.0, "ACTIVE"),
    (6, "PRD006", "Onboarding Session", "SERVICE", 3499.0, "ACTIVE"),
    (7, "PRD007", "Team Training", "SERVICE", 4999.0, "ACTIVE"),
    (8, "PRD008", "Custom Dashboard", "SERVICE", 5999.0, "ACTIVE"),
    (9, "PRD009", "Advanced Reporting", "ADD_ON", 1799.0, "ACTIVE"),
    (10, "PRD010", "API Usage Pack", "ADD_ON", 1299.0, "ACTIVE"),
    (11, "PRD011", "Storage Extension", "ADD_ON", 899.0, "ACTIVE"),
    (12, "PRD012", "Security Review", "SERVICE", 4499.0, "ACTIVE"),
    (13, "PRD013", "Migration Support", "SERVICE", 5499.0, "ACTIVE"),
    (14, "PRD014", "Workflow Templates", "ADD_ON", 1199.0, "ACTIVE"),
    (15, "PRD015", "Insights Pack", "ADD_ON", 1599.0, "ACTIVE"),
    (16, "PRD016", "Consulting Hour", "SERVICE", 1999.0, "ACTIVE"),
    (17, "PRD017", "Data Quality Pack", "ADD_ON", 2099.0, "ACTIVE"),
    (18, "PRD018", "Governance Pack", "ADD_ON", 2599.0, "ACTIVE"),
    (19, "PRD019", "Legacy Connector", "ADD_ON", 1399.0, "INACTIVE"),
    (20, "PRD020", "Benchmark Report", "SERVICE", 999.0, "ACTIVE"),
]

FIRST = ["Aarav","Vivaan","Aditya","Arjun","Sai","Rohan","Karthik","Rahul","Nikhil","Varun",
         "Ananya","Diya","Ishita","Meera","Kavya","Sneha","Priya","Aditi","Nandini","Riya"]
LAST = ["Sharma","Reddy","Rao","Patel","Verma","Gupta","Iyer","Nair","Kumar","Singh",
        "Mehta","Joshi","Kapoor","Das","Bose","Menon","Kulkarni","Chauhan","Naidu","Mishra"]
PAYMENT_METHODS = ["CARD", "UPI", "NET_BANKING", "WALLET"]
REFUND_REASONS = ["Duplicate charge","Service dissatisfaction","Billing correction","Plan change","Order issue"]

def write_csv(name, header, rows):
    path = ROOT / name
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"{name}: {len(rows):,} rows")

def random_date(start, end):
    return start + timedelta(days=random.randint(0, (end-start).days))

def month_iter(start, end):
    current = date(start.year, start.month, 1)
    while current <= end:
        yield current
        current = date(current.year + (current.month == 12), 1 if current.month == 12 else current.month + 1, 1)

write_csv("regions.csv", ["region_id","region_code","region_name"], REGIONS)
write_csv("products.csv", ["product_id","product_code","product_name","category","unit_price","product_status"], PRODUCTS)

customers = []
for cid in range(1, 1001):
    region_id = random.choices([1,2,3,4], weights=[24,30,22,24], k=1)[0]
    signup = random_date(date(2025,1,1), date(2026,8,15))
    status = random.choices(["ACTIVE","INACTIVE","SUSPENDED","CLOSED"], weights=[82,9,5,4], k=1)[0]
    name = f"{random.choice(FIRST)} {random.choice(LAST)}"
    customers.append([cid, f"CUST{cid:05d}", name, region_id, signup.isoformat(), status])

write_csv("customers.csv",
          ["customer_id","customer_code","customer_name","region_id","signup_date","account_status"],
          customers)

subscriptions = []
sub_id = 1
for row in customers:
    cid, _, _, region_id, signup_iso, account_status = row
    signup = date.fromisoformat(signup_iso)
    plan = random.choices(["FREE","BASIC","PRO","ENTERPRISE"], weights=[10,42,38,10], k=1)[0]
    start_date = max(signup, random_date(date(2025,1,1), date(2026,6,30)))

    cancelled = random.random() < 0.08
    south_pro_anomaly = (plan == "PRO" and region_id == 2 and random.random() < 0.24)
    if south_pro_anomaly:
        cancelled = True

    status = "ACTIVE"
    end_date = ""
    if cancelled:
        cancel_date = random_date(date(2026,8,1), date(2026,8,28)) if south_pro_anomaly \
                      else random_date(date(2026,2,1), date(2026,8,28))
        if cancel_date >= start_date:
            status = "CANCELLED"
            end_date = cancel_date.isoformat()

    if account_status == "CLOSED" and status == "ACTIVE":
        exp = random_date(max(start_date, date(2026,1,1)), date(2026,8,28))
        status = "EXPIRED"
        end_date = exp.isoformat()

    subscriptions.append([sub_id, cid, plan, status, start_date.isoformat(), end_date, f"{PLANS[plan]:.2f}"])
    sub_id += 1

write_csv("subscriptions.csv",
          ["subscription_id","customer_id","plan_name","subscription_status","start_date","end_date","monthly_price"],
          subscriptions)

sub_by_customer = {r[1]: r for r in subscriptions}
payments = []
successful = []
pid = 1

for row in customers:
    cid, _, _, region_id, _, _ = row
    sub = sub_by_customer[cid]
    sid, plan, status = sub[0], sub[2], sub[3]
    sub_start = date.fromisoformat(sub[4])
    sub_end = date.fromisoformat(sub[5]) if sub[5] else None
    monthly_price = float(sub[6])
    if monthly_price <= 0:
        continue

    for month_start in month_iter(START_DATE, END_DATE):
        bill_day = random.randint(1,25)
        pay_date = date(month_start.year, month_start.month, bill_day)
        if pay_date < sub_start:
            continue
        if sub_end and pay_date > sub_end:
            continue

        failure_rate = 0.05
        if pay_date.month == 8:
            failure_rate = 0.09
            if region_id == 2:
                failure_rate = 0.18
                if plan == "PRO":
                    failure_rate = 0.24

        roll = random.random()
        if roll < failure_rate:
            pstatus = "FAILED"
        elif roll < failure_rate + 0.015:
            pstatus = "PENDING"
        else:
            pstatus = "SUCCESS"

        ts = datetime(pay_date.year, pay_date.month, pay_date.day,
                      random.randint(8,20), random.randint(0,59), 0)
        payments.append([pid, cid, sid, f"{monthly_price:.2f}", pstatus,
                         ts.isoformat(sep=" "), random.choice(PAYMENT_METHODS)])
        if pstatus == "SUCCESS":
            successful.append((pid, cid, monthly_price, pay_date, region_id, plan))
        pid += 1

write_csv("payments.csv",
          ["payment_id","customer_id","subscription_id","amount","payment_status","payment_date","payment_method"],
          payments)

refunds = []
rid = 1
for pid, cid, amount, pay_date, region_id, plan in successful:
    prob = 0.03
    if pay_date.month == 8:
        prob = 0.07
        if region_id == 2:
            prob = 0.10
    if random.random() < prob:
        frac = random.choice([0.25,0.50,1.00])
        refund_amount = round(amount*frac, 2)
        rd = min(pay_date + timedelta(days=random.randint(1,12)), END_DATE)
        ts = datetime(rd.year, rd.month, rd.day, random.randint(9,18), random.randint(0,59), 0)
        refunds.append([rid, pid, cid, f"{refund_amount:.2f}", random.choice(REFUND_REASONS), ts.isoformat(sep=" ")])
        rid += 1

write_csv("refunds.csv",
          ["refund_id","payment_id","customer_id","refund_amount","refund_reason","refund_date"],
          refunds)

product_lookup = {p[0]: p for p in PRODUCTS}
orders = []
oid = 1
for _ in range(4200):
    cid = random.randint(1,1000)
    region_id = customers[cid-1][3]
    product_id = random.randint(1,20)
    unit_price = product_lookup[product_id][4]
    qty = random.choices([1,2,3,4], weights=[66,22,9,3], k=1)[0]
    od = random_date(START_DATE, END_DATE)

    if od.month == 8 and region_id == 2 and random.random() < 0.30:
        ostatus = random.choice(["CANCELLED","REFUNDED"])
    else:
        ostatus = random.choices(["COMPLETED","CANCELLED","PENDING","REFUNDED"], weights=[84,7,5,4], k=1)[0]

    ts = datetime(od.year, od.month, od.day, random.randint(8,21), random.randint(0,59), 0)
    orders.append([oid, cid, product_id, qty, f"{unit_price*qty:.2f}", ostatus, ts.isoformat(sep=" ")])
    oid += 1

write_csv("orders.csv",
          ["order_id","customer_id","product_id","quantity","order_amount","order_status","order_date"],
          orders)

print("Synthetic data complete.")
print("Ground truth: August underperforms July, with South/PRO weakness, higher failures, refunds, and cancellations.")

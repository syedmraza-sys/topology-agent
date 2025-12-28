import csv
import random 

# Define pools for random generation
severities = ["High", "Medium", "Low", "Critical"]
components = ["Router", "Switch", "Firewall", "LoadBalancer", "FiberLink", "PowerSupply"]
locations = ["DataCenter-A", "POP-North", "POP-South", "HQ-Basement", "Cloud-Region-East"]
issues = [
    "Overheating detected",
    "Packet loss > 1%",
    "Interface flapping",
    "BGP neighbor down",
    "OSPF state stuck",
    "High latency observed",
    "Memory allocation failure",
    "Fan failure",
    "Optical signal low",
    "CRC errors increasing"
]

def generate_row(index):
    cid = f"CMT-{1000 + index}"
    issue = random.choice(issues)
    comp = random.choice(components)
    loc = random.choice(locations)
    
    text = f"Warning: {comp} at {loc} is reporting {issue}. Ticket auto-generated."
    
    # Randomly vary the text
    if index % 3 == 0:
        text = f"Maintenance alert: {comp} in {loc} scheduled for reboot due to {issue}."
    elif index % 4 == 0:
        text = f"Critical: {issue} on {comp} ({loc}). Immediate attention required."
        
    tid = f"TKT-{5000 + index}"
    author = f"system_monitor_{random.randint(1,5)}@netops.com"
    
    return [cid, text, tid, author]

records = []
headers = ["id", "text", "ticket_id", "author"]

for i in range(1, 101):
    records.append(generate_row(i))

filename = "comments_100.csv"
try:
    with open(filename, "w", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(records)
    print(f"Successfully created {filename} with 100 comments.")
except Exception as e:
    print(f"Error writing file: {e}")

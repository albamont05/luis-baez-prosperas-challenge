import time
import requests
import sys

BASE_URL = "http://localhost:8000"

def wait_for_api():
    for _ in range(15):
        try:
            res = requests.get(f"{BASE_URL}/health")
            if res.status_code == 200:
                print("API is ready")
                return True
        except:
            pass
        time.sleep(2)
    return False

if not wait_for_api():
    print("API not ready")
    sys.exit(1)

print("\n1. Registering user...")
res = requests.post(f"{BASE_URL}/register", json={"username": "testuser", "password": "testpassword"})
if res.status_code == 201:
    print("User registered", res.json())
elif res.status_code == 400:
    print("User already registered", res.json())
else:
    print("Failed to register:", res.status_code, res.text)

print("\n2. Logging in...")
res = requests.post(f"{BASE_URL}/login", data={"username": "testuser", "password": "testpassword"})
if res.status_code != 200:
    print("Failed to login", res.status_code, res.text)
    sys.exit(1)
token = res.json()["access_token"]
print("Logged in, token:", token[:10] + "...")

headers = {"Authorization": f"Bearer {token}"}

print("\n3. Creating a Job...")
res = requests.post(f"{BASE_URL}/jobs", json={"report_type": "CSV"}, headers=headers)
if res.status_code != 202:
    print("Failed to create job", res.status_code, res.text)
    sys.exit(1)
job = res.json()
print("Job created:", job)
job_id = job["job_id"]

print("\n4. Fetching job status loop...")
for _ in range(10):
    time.sleep(2)
    res = requests.get(f"{BASE_URL}/jobs/{job_id}", headers=headers)
    if res.status_code != 200:
        print("Failed to fetch job", res.status_code, res.text)
        continue
    job_status = res.json()
    print(f"Status check: {job_status['status']}")
    if job_status["status"] == "COMPLETED" or job_status["status"] == "FAILED":
        print("Final job state:", job_status)
        break

print("\n5. Listing jobs...")
res = requests.get(f"{BASE_URL}/jobs?skip=0&limit=20", headers=headers)
if res.status_code == 200:
    print("Jobs list:", len(res.json()), "jobs found")
    print(res.json())
else:
    print("Failed to list jobs", res.status_code, res.text)

print("\n6. Intentional Error global handler Check")
res = requests.get(f"{BASE_URL}/jobs/not-a-uuid", headers=headers)
print("Error payload:", res.status_code, res.text)

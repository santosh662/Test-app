================================================================
TASKFLOW — OBSERVABILITY TRAINING STACK
Complete Setup & Usage Guide
================================================================

WHAT IS THIS
------------
TaskFlow is a demo Task Manager application built specifically
for teaching Observability concepts in a DevOps classroom.

The full stack includes:
  - TaskFlow App      (Python Flask, custom Prometheus metrics)
  - Prometheus        (metrics collection and alerting)
  - AlertManager      (email notifications)
  - Grafana           (dashboards and visualization)
  - Node Exporter     (system-level metrics)
  - cAdvisor          (Docker container metrics)
  - Loki              (log aggregation — Session 2)
  - Promtail          (log collector — Session 2)

Everything runs in Docker containers.
One command starts the entire stack.


================================================================
FOLDER STRUCTURE
================================================================

full_obs/
  app/
    app.py                   Flask application + Prometheus metrics
    Dockerfile               Container image definition
    requirements.txt         Python dependencies (flask, prometheus-client)
    templates/
      index.html             Frontend UI (dark theme)
  alertmanager/
    alertmanager.yml         Email alert configuration (edit this)
  loki/
    loki-config.yml          Loki log storage configuration
  promtail/
    promtail-config.yml      Log collector configuration
  prometheus.yml             Prometheus scrape targets
  alert_rules.yml            Alert conditions (7 rules)
  docker-compose.yml         Session 1 stack (6 services)
  docker-compose-session2.yml  Session 2 stack (8 services + Loki)


================================================================
PREREQUISITES
================================================================

1. AWS EC2 instance
   OS:            Ubuntu 22.04 LTS
   Instance type: t2.large (minimum — 2 vCPU, 8GB RAM)

   Why t2.large:
   Prometheus + Grafana + cAdvisor together need at least 4GB RAM.
   t2.micro and t2.small will run out of memory.

2. Security Group — open these inbound ports:

   Port    Service
   ----    -------
   22      SSH access
   3000    Grafana dashboard
   8000    TaskFlow application
   8080    cAdvisor dashboard
   9090    Prometheus dashboard
   9093    AlertManager dashboard
   9100    Node Exporter metrics

3. A Gmail account with App Password generated
   (instructions in the Email Configuration section below)

4. SSH key pair (.pem file)


================================================================
STEP 1 — CONNECT TO EC2
================================================================

From your local machine (PowerShell or Terminal):

    ssh -i your-key.pem ubuntu@<EC2-PUBLIC-IP>

Replace:
  your-key.pem      with your actual key file path
  <EC2-PUBLIC-IP>   with your EC2 instance's public IP address


================================================================
STEP 2 — INSTALL DOCKER
================================================================

Run these commands one by one on the EC2 instance:

    sudo apt update && sudo apt upgrade -y

    sudo apt install -y ca-certificates curl gnupg lsb-release

    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
      | sudo gpg --dearmor -o /usr/share/keyrings/docker.gpg

    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker.gpg] \
      https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
      | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    sudo apt update

    sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

    sudo usermod -aG docker $USER && newgrp docker

Verify Docker is installed:

    docker --version
    docker compose version

Expected output:
    Docker version 24.x.x
    Docker Compose version v2.x.x


================================================================
STEP 3 — UPLOAD PROJECT FILES TO EC2
================================================================

From your LOCAL machine (not the EC2 terminal):

Option A — Using SCP (recommended):

    scp -i your-key.pem full_taskflow.zip ubuntu@<EC2-PUBLIC-IP>:~/

Then on EC2:

    cd ~
    sudo apt install -y unzip
    unzip full_taskflow.zip
    mv full_obs taskmanager

Option B — Using Git (if you push to GitHub):

    git clone https://github.com/your-repo/taskmanager.git

Verify the folder structure:

    ls ~/taskmanager/

You should see:
    app/  alertmanager/  loki/  promtail/
    prometheus.yml  alert_rules.yml
    docker-compose.yml  docker-compose-session2.yml


================================================================
STEP 4 — CONFIGURE EMAIL ALERTS
================================================================

Before starting the stack, configure your Gmail credentials
in the AlertManager configuration file.

HOW TO GET A GMAIL APP PASSWORD:
  1. Go to myaccount.google.com
  2. Click Security in the left menu
  3. Under "How you sign in to Google" — enable 2-Step Verification
     (required before App Passwords can be created)
  4. Go back to Security → scroll down → App passwords
  5. Select app: Mail
  6. Select device: Other (Custom name) → type "AlertManager"
  7. Click Generate
  8. Copy the 16-character password shown (spaces don't matter)

Now edit the AlertManager config:

    vim ~/taskmanager/alertmanager/alertmanager.yml

Replace these 4 values with your actual Gmail address and
App Password:

    smtp_from:          'YOUR_GMAIL@gmail.com'
    smtp_auth_username: 'YOUR_GMAIL@gmail.com'
    smtp_auth_password: 'YOUR_16_CHAR_APP_PASSWORD'
    to:                 'YOUR_GMAIL@gmail.com'

Save the file: press Esc, type :wq, press Enter.

NOTE: The "to" address is where alerts will be delivered.
It can be the same Gmail or a different email address.


================================================================
STEP 5 — START THE STACK (SESSION 1)
================================================================

    cd ~/taskmanager
    docker compose up -d --build

The first run will:
  - Build the TaskFlow app Docker image (~2 minutes)
  - Pull Prometheus, Grafana, cAdvisor images from Docker Hub
  - Start all 6 containers

Check all containers are running:

    docker ps

Expected output — 6 containers with STATUS "Up":
    taskmanager
    prometheus
    alertmanager
    grafana
    node-exporter
    cadvisor

If any container is not running, check its logs:

    docker logs <container-name>


================================================================
STEP 6 — VERIFY ALL SERVICES
================================================================

Open these URLs in your browser.
Replace <EC2-IP> with your actual EC2 public IP.

    Service          URL                              Login
    -------          ---                              -----
    TaskFlow App     http://<EC2-IP>:8000             (none)
    App Metrics      http://<EC2-IP>:8000/metrics     (none)
    App Health       http://<EC2-IP>:8000/health      (none)
    Prometheus       http://<EC2-IP>:9090             (none)
    AlertManager     http://<EC2-IP>:9093             (none)
    cAdvisor         http://<EC2-IP>:8080             (none)
    Grafana          http://<EC2-IP>:3000             admin / admin


================================================================
STEP 7 — PROMETHEUS TARGETS CHECK
================================================================

In Prometheus dashboard:
  Click Status → Targets

All 4 targets must show State: UP

    Job            URL                        State
    ---            ---                        -----
    prometheus     localhost:9090             UP
    node-exporter  node-exporter:9100         UP
    cadvisor       cadvisor:8080              UP
    taskmanager    taskmanager:8000           UP

If any target shows DOWN:
  - Check that the container is running: docker ps
  - Check container logs: docker logs <container-name>
  - Verify the Security Group has the correct port open


================================================================
STEP 8 — GRAFANA SETUP
================================================================

8A. Login and Change Password
    Open http://<EC2-IP>:3000
    Username: admin
    Password: admin
    Change password when prompted.

8B. Add Prometheus Data Source
    1. Click Connections in the left menu
    2. Click Data sources
    3. Click Add data source
    4. Select Prometheus
    5. In the URL field enter: http://prometheus:9090
       (use the container name, not the EC2 IP)
    6. Scroll down and click Save & Test
    7. Green message should appear: "Successfully queried the Prometheus API"

8C. Import Node Exporter Dashboard
    1. Click Dashboards in the left menu
    2. Click New → Import
    3. In "Import via grafana.com" field, enter: 1860
    4. Click Load
    5. Select Prometheus as the data source
    6. Click Import

    This dashboard shows:
    - CPU usage per core
    - Memory usage and available RAM
    - Disk I/O read/write
    - Network traffic in/out
    - System load average

8D. Import cAdvisor Dashboard
    1. Click Dashboards → New → Import
    2. Enter ID: 893 → Load
    3. Select Prometheus → Import

    This dashboard shows:
    - Per-container CPU usage
    - Per-container memory usage
    - Container uptime
    - Running containers list

8E. Create TaskFlow Custom Dashboard (Live Classroom Exercise)
    1. Click Dashboards → New → New dashboard
    2. Click Add visualization

    Create these 5 panels one by one:

    Panel 1 — Active Pending Tasks
      Query:          active_tasks_current
      Visualization:  Stat
      Title:          Active Pending Tasks
      Thresholds:     0-5 = green, 5-10 = yellow, 10+ = red

    Panel 2 — Task Creation Rate
      Query:          rate(tasks_created_total[5m])
      Visualization:  Time series
      Title:          Task Creation Rate
      Legend:         {{priority}}

    Panel 3 — HTTP Request Rate
      Query:          sum(rate(http_requests_total[1m])) by (endpoint)
      Visualization:  Time series
      Title:          HTTP Requests per Second

    Panel 4 — Response Time p95
      Query:          histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
      Visualization:  Gauge
      Title:          Response Time p95
      Unit:           seconds

    Panel 5 — Completed Tasks by Priority
      Query:          tasks_completed_total
      Visualization:  Bar chart
      Title:          Completed Tasks by Priority
      Legend:         {{priority}}

    Save the dashboard with name: TaskFlow Overview


================================================================
STEP 9 — DEMO BUTTONS (CLASSROOM USE)
================================================================

The TaskFlow app has two demo buttons in the left panel
under "Demo Controls":

SIMULATE LOAD BUTTON (yellow):
  - Creates 10 tasks automatically with mixed priorities
  - Includes critical, high, medium, and low priority tasks
  - After ~1 minute, triggers the TooManyPendingTasks alert
  - Use this to demonstrate alert firing without manually
    adding tasks one by one

SIMULATE ERRORS BUTTON (red):
  - Injects 20 HTTP 500 error metrics into Prometheus
  - After ~1 minute, triggers the HighHTTPErrorRate alert
  - Use this to demonstrate the error rate alert
  - This is the only way to trigger this alert in a demo

DEMO SEQUENCE FOR CLASSROOM:
  1. Click Simulate Load → watch active_tasks_current rise in Grafana
  2. Wait 1 minute → TooManyPendingTasks fires in Prometheus
  3. Check email → [FIRING] alert received
  4. Click Simulate Errors → watch http_requests_total in Grafana
  5. Wait 1 minute → HighHTTPErrorRate fires
  6. Complete all tasks in the app
  7. Wait 1 minute → alerts resolve
  8. Check email → [RESOLVED] emails received


================================================================
STEP 10 — ALERT RULES REFERENCE
================================================================

These 7 alert rules are defined in alert_rules.yml:

    Alert                  Condition                    Severity
    -----                  ---------                    --------
    TooManyPendingTasks    active_tasks > 5 for 1m      warning
    CriticalTaskPending    critical tasks pending > 2m  critical
    HighHTTPErrorRate      5xx rate > 0.05/s for 1m     warning
    TaskManagerDown        app unreachable for 30s      critical
    HighCPUUsage           CPU > 80% for 2m             warning
    HighMemoryUsage        Memory > 80% for 2m          warning
    LowDiskSpace           Disk < 20% for 1m            critical

To view alert status:
  Prometheus → Alerts (http://<EC2-IP>:9090/alerts)

States:
  Inactive  = condition is not currently true
  Pending   = condition is true but "for" duration not reached yet
  Firing    = alert is active, notification sent


================================================================
STEP 11 — SESSION 2: ADD LOKI FOR LOGS
================================================================

Session 2 adds Loki (log storage) and Promtail (log collector)
to the existing stack.

Stop Session 1 stack:

    cd ~/taskmanager
    docker compose down

Start Session 2 stack with Loki:

    docker compose -f docker-compose-session2.yml up -d

Verify all 8 containers are running:

    docker ps

New containers added:
    loki      — port 3100
    promtail  — no exposed port (reads Docker logs internally)

Verify Loki is ready:

    curl http://localhost:3100/ready

Expected: ready


================================================================
STEP 12 — GRAFANA LOKI SETUP
================================================================

12A. Add Loki Data Source
     1. Grafana → Connections → Data sources → Add data source
     2. Select Loki
     3. URL: http://loki:3100
     4. Save & Test → green success message

12B. Explore Logs
     1. Click Explore in the left menu
     2. Select Loki as the data source (top dropdown)
     3. Run this query:
            {container="taskmanager"}
     4. Click Run Query
     5. Live logs from the TaskFlow app will appear

12C. LogQL Queries to Try

     All TaskFlow logs:
       {container="taskmanager"}

     Only task creation logs:
       {container="taskmanager"} |= "Task created"

     Only task completion logs:
       {container="taskmanager"} |= "Task completed"

     Only warning level logs:
       {container="taskmanager"} |= "warning"

     Only critical priority task logs:
       {container="taskmanager"} |= "critical"

     JSON parsed with formatted output:
       {container="taskmanager"} | json | line_format "{{.level}}: {{.message}}"

12D. Add Logs Panel to TaskFlow Dashboard
     1. Open the TaskFlow Overview dashboard
     2. Click Edit → Add visualization
     3. Select Loki as data source
     4. Query: {container="taskmanager"} |= "Task created"
     5. Visualization: Logs
     6. Title: Recent Task Activity
     7. Save

     Now the dashboard shows both metrics panels and
     a live log feed — metrics and logs on one screen.

12E. Metrics + Logs Correlation Demo
     1. Click Simulate Load button in the app
     2. Watch Active Pending Tasks panel rise (metrics)
     3. Watch Recent Task Activity panel (logs) — each task
        creation appears as a log entry in real time
     4. After 1 minute → alert fires
     5. Complete tasks → metrics drop, logs show completions
     6. Alert resolves — resolved email arrives

     Key teaching point:
     Metrics showed WHAT happened (task count exceeded threshold)
     Logs showed WHY / WHICH ones (exact task details, priorities)
     This is the difference between monitoring and observability.


================================================================
APP METRICS REFERENCE
================================================================

These metrics are exposed at http://<EC2-IP>:8000/metrics

    Metric                                    Type      Description
    ------                                    ----      -----------
    active_tasks_current                      Gauge     Current pending tasks
    completed_tasks_current                   Gauge     Current completed tasks
    tasks_created_total{priority}             Counter   Tasks created by priority
    tasks_completed_total{priority}           Counter   Tasks completed by priority
    tasks_deleted_total                       Counter   Tasks deleted
    http_requests_total{method,endpoint,status} Counter HTTP requests
    http_request_duration_seconds             Histogram Request latency


================================================================
CLEANUP
================================================================

Stop stack and remove volumes (all data deleted):

    docker compose down -v

Or for Session 2:

    docker compose -f docker-compose-session2.yml down -v

Stop stack but keep data (volumes preserved):

    docker compose down

Terminate EC2 from AWS Console:
    EC2 → Instances → select instance → Instance state → Terminate

NOTE: Terminating the instance stops all billing.
Key Pairs and Security Groups are free — no need to delete them.


================================================================
COMMON ERRORS AND FIXES
================================================================

ERROR: Port already in use
  Fix: Check if another service is using that port
       sudo lsof -i :<port-number>

ERROR: docker compose not found
  Fix: sudo apt install -y docker-compose-plugin

ERROR: Permission denied (docker)
  Fix: sudo usermod -aG docker $USER && newgrp docker

ERROR: Grafana "Data source connected but no labels found"
  Fix: Make sure TaskFlow app is running and has received
       some requests. Click Simulate Load button first.

ERROR: SonarQube / Loki container keeps restarting
  Fix: Check memory — run: free -h
       If less than 2GB available, the instance is too small.
       Use t2.large or larger.

ERROR: Alerts not sending email
  Fix 1: Verify App Password is correct in alertmanager.yml
  Fix 2: Check AlertManager logs: docker logs alertmanager
  Fix 3: Verify alert is in FIRING state (not just Pending)
         in Prometheus → Alerts page
  Fix 4: Check spam/junk folder

ERROR: Prometheus target shows DOWN
  Fix: Check container is running: docker ps
       Check logs: docker logs <container-name>
       Verify Security Group port is open

ERROR: Grafana shows "No data"
  Fix: Make sure Prometheus data source URL is
       http://prometheus:9090 (container name, not EC2 IP)
       Make sure the time range includes recent data

ERROR: curl: (7) Failed to connect on port 3100
  Fix: Loki takes ~30 seconds to start
       Wait and retry: curl http://localhost:3100/ready


================================================================
QUICK REFERENCE — ALL URLS
================================================================

    http://<EC2-IP>:8000          TaskFlow App
    http://<EC2-IP>:8000/metrics  Raw Prometheus metrics
    http://<EC2-IP>:8000/health   App health check
    http://<EC2-IP>:8000/api/stats  Task statistics (JSON)
    http://<EC2-IP>:9090          Prometheus
    http://<EC2-IP>:9090/alerts   Alert status
    http://<EC2-IP>:9090/targets  Scrape targets status
    http://<EC2-IP>:9093          AlertManager
    http://<EC2-IP>:3000          Grafana  (admin/admin)
    http://<EC2-IP>:8080          cAdvisor
    http://<EC2-IP>:9100/metrics  Node Exporter raw metrics
    http://<EC2-IP>:3100/ready    Loki health (Session 2)


================================================================
GRAFANA DASHBOARD IDs
================================================================

    1860    Node Exporter Full — system metrics
    893     cAdvisor — Docker container metrics
    Manual  TaskFlow Overview — create in classroom


================================================================
END OF README
================================================================

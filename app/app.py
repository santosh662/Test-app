from flask import Flask, request, jsonify, render_template
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
import time
import uuid
import logging
import json
import sys

app = Flask(__name__)

# ── Structured JSON Logger ────────────────────────────────────────────────────
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S'),
            "level":     record.levelname,
            "service":   "taskmanager",
            "message":   record.getMessage(),
        }
        if hasattr(record, 'extra'):
            log_data.update(record.extra)
        return json.dumps(log_data)

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JSONFormatter())
logger  = logging.getLogger("taskmanager")
logger.setLevel(logging.INFO)
logger.addHandler(handler)
logger.propagate = False

def log(level, message, **kwargs):
    record = logging.LogRecord(
        name="taskmanager", level=getattr(logging, level.upper()),
        pathname="", lineno=0, msg=message, args=(), exc_info=None
    )
    record.extra = kwargs
    logger.handle(record)

# ── Prometheus Metrics ────────────────────────────────────────────────────────
tasks_created   = Counter('tasks_created_total',   'Total tasks created',   ['priority'])
tasks_completed = Counter('tasks_completed_total', 'Total tasks completed', ['priority'])
tasks_deleted   = Counter('tasks_deleted_total',   'Total tasks deleted')
active_tasks    = Gauge('active_tasks_current',    'Current pending tasks')
completed_gauge = Gauge('completed_tasks_current', 'Current completed tasks')
http_requests   = Counter('http_requests_total',   'Total HTTP requests',   ['method', 'endpoint', 'status'])
http_duration   = Histogram('http_request_duration_seconds', 'HTTP request latency',
                            ['method', 'endpoint'],
                            buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5])

# ── In-memory store ───────────────────────────────────────────────────────────
tasks = {}

def update_gauges():
    active_tasks.set(sum(1 for t in tasks.values() if not t['completed']))
    completed_gauge.set(sum(1 for t in tasks.values() if t['completed']))

# ── Request middleware ────────────────────────────────────────────────────────
@app.before_request
def start_timer():
    request._start_time = time.time()

@app.after_request
def record_request(response):
    if request.path == '/metrics':
        return response
    duration = time.time() - request._start_time
    endpoint = request.path
    status   = response.status_code
    http_requests.labels(method=request.method, endpoint=endpoint, status=status).inc()
    http_duration.labels(method=request.method, endpoint=endpoint).observe(duration)
    log("info", "HTTP request",
        method=request.method, path=endpoint,
        status=status, duration_ms=round(duration * 1000, 2))
    return response

# ── Routes ────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    return jsonify(list(tasks.values()))

@app.route('/api/tasks', methods=['POST'])
def create_task():
    data     = request.json or {}
    title    = data.get('title', '').strip()
    priority = data.get('priority', 'medium')

    if not title:
        log("warning", "Task creation failed — empty title")
        return jsonify({'error': 'Title is required'}), 400

    task_id = str(uuid.uuid4())[:8]
    task = {
        'id':          task_id,
        'title':       title,
        'description': data.get('description', '').strip(),
        'priority':    priority,
        'completed':   False,
        'created_at':  time.strftime('%Y-%m-%d %H:%M:%S')
    }
    tasks[task_id] = task
    tasks_created.labels(priority=priority).inc()
    update_gauges()

    log("info", "Task created",
        task_id=task_id, title=title,
        priority=priority, total_active=sum(1 for t in tasks.values() if not t['completed']))
    return jsonify(task), 201

@app.route('/api/tasks/<task_id>/complete', methods=['PUT'])
def complete_task(task_id):
    if task_id not in tasks:
        log("warning", "Task complete failed — not found", task_id=task_id)
        return jsonify({'error': 'Task not found'}), 404

    task = tasks[task_id]
    if task['completed']:
        log("warning", "Task already completed", task_id=task_id, title=task['title'])
        return jsonify({'error': 'Already completed'}), 400

    tasks[task_id]['completed'] = True
    tasks_completed.labels(priority=task['priority']).inc()
    update_gauges()

    log("info", "Task completed",
        task_id=task_id, title=task['title'], priority=task['priority'],
        remaining_active=sum(1 for t in tasks.values() if not t['completed']))
    return jsonify(tasks[task_id])

@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    if task_id not in tasks:
        log("warning", "Task delete failed — not found", task_id=task_id)
        return jsonify({'error': 'Task not found'}), 404

    task = tasks.pop(task_id)
    tasks_deleted.inc()
    update_gauges()

    log("info", "Task deleted",
        task_id=task_id, title=task['title'], priority=task['priority'])
    return jsonify({'status': 'deleted'})

@app.route('/api/stats', methods=['GET'])
def stats():
    pending   = sum(1 for t in tasks.values() if not t['completed'])
    completed = sum(1 for t in tasks.values() if t['completed'])
    by_priority = {p: sum(1 for t in tasks.values()
                          if t['priority'] == p and not t['completed'])
                   for p in ['low', 'medium', 'high', 'critical']}
    return jsonify({
        'total': len(tasks), 'pending': pending,
        'completed': completed, 'by_priority': by_priority
    })

@app.route('/api/simulate/load', methods=['POST'])
def simulate_load():
    """Create 10 tasks automatically — for classroom alert demo."""
    demo_tasks = [
        ("Deploy to Production",     "critical"),
        ("Database Backup",          "high"),
        ("SSL Certificate Renewal",  "critical"),
        ("Update Dependencies",      "medium"),
        ("Code Review PR #142",      "high"),
        ("Fix Login Bug",            "critical"),
        ("Write Unit Tests",         "medium"),
        ("Update API Docs",          "low"),
        ("Security Audit",           "high"),
        ("Performance Testing",      "medium"),
    ]
    created = []
    for title, priority in demo_tasks:
        task_id = str(uuid.uuid4())[:8]
        task = {
            'id':          task_id,
            'title':       title,
            'description': 'Auto-generated for demo',
            'priority':    priority,
            'completed':   False,
            'created_at':  time.strftime('%Y-%m-%d %H:%M:%S')
        }
        tasks[task_id] = task
        tasks_created.labels(priority=priority).inc()
        created.append(task_id)

    update_gauges()
    log("warning", "Simulate load triggered",
        tasks_created=len(created),
        total_active=sum(1 for t in tasks.values() if not t['completed']))
    return jsonify({'status': 'ok', 'tasks_created': len(created)})


@app.route('/api/simulate/errors', methods=['POST'])
def simulate_errors():
    """Generate HTTP 500 errors — for HighHTTPErrorRate alert demo."""
    count = int((request.json or {}).get('count', 20))
    for _ in range(count):
        http_requests.labels(method='GET', endpoint='/api/tasks', status=500).inc()
    log("error", "Simulate errors triggered", error_count=count)
    return jsonify({'status': 'ok', 'errors_injected': count})


@app.route('/metrics')
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

@app.route('/health')
def health():
    log("info", "Health check", status="healthy", task_count=len(tasks))
    return jsonify({'status': 'healthy', 'tasks': len(tasks)})

if __name__ == '__main__':
    log("info", "TaskFlow app starting", port=8000)
    app.run(host='0.0.0.0', port=8000, debug=False)

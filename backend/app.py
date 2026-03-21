import json
import os
import re
from datetime import date, datetime, timedelta
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity
)
import requests
from sqlalchemy import func
from models import Task, Session, User

ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(ENV_PATH, override=True)

app = Flask(__name__)

app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
jwt = JWTManager(app)

CORS(app)
session = Session()


def normalize_category(raw_category):
    value = (raw_category or "").strip()
    if not value:
        return "General"
    return " ".join(part.capitalize() for part in value.split())


def summarize_tasks_for_ai(tasks):
    today = date.today()
    overdue = [t for t in tasks if t.due_date and t.due_date < today and not t.completed]
    upcoming = [t for t in tasks if t.due_date and t.due_date >= today and not t.completed]
    completed = [t for t in tasks if t.completed]

    upcoming_sorted = sorted(upcoming, key=lambda item: item.due_date)[:12]

    return {
        "today": today.isoformat(),
        "total": len(tasks),
        "completed": len(completed),
        "overdue": len(overdue),
        "upcoming": [
            {
                "id": task.id,
                "title": task.title,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "category": task.category or "General",
            }
            for task in upcoming_sorted
        ],
    }


def parse_json_from_text(raw_text):
    text = (raw_text or "").strip()
    if not text:
        return None

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None


def call_groq(messages, temperature=0.3):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None, "Missing GROQ_API_KEY"

    model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
            },
            timeout=20,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return content, None
    except Exception as exc:
        return None, str(exc)


def build_due_this_week_response(tasks):
    today = date.today()
    end_of_week = today + timedelta(days=(6 - today.weekday()))
    due_this_week = [
        task
        for task in tasks
        if task.due_date and today <= task.due_date <= end_of_week and not task.completed
    ]
    due_this_week = sorted(due_this_week, key=lambda item: item.due_date)

    if not due_this_week:
        return "No incomplete tasks are due this week. Nice runway."

    lines = ["Here are your tasks due this week:"]
    for task in due_this_week[:8]:
        lines.append(f"- {task.title} (due {task.due_date.isoformat()})")

    if len(due_this_week) > 8:
        lines.append(f"...and {len(due_this_week) - 8} more.")

    return "\n".join(lines)


def build_overdue_response(tasks):
    today = date.today()
    overdue = [task for task in tasks if task.due_date and task.due_date < today and not task.completed]
    overdue = sorted(overdue, key=lambda item: item.due_date)

    if not overdue:
        return "You have no overdue tasks right now."

    lines = [f"You have {len(overdue)} overdue task(s):"]
    for task in overdue[:8]:
        lines.append(f"- {task.title} (was due {task.due_date.isoformat()})")

    if len(overdue) > 8:
        lines.append(f"...and {len(overdue) - 8} more.")

    return "\n".join(lines)


def build_completed_summary(tasks):
    total = len(tasks)
    completed = len([task for task in tasks if task.completed])
    pending = total - completed
    completion_rate = round((completed / total) * 100) if total else 0

    return (
        f"Completed: {completed} of {total} tasks ({completion_rate}%). "
        f"Remaining: {pending}."
    )


def looks_like_task_creation(query):
    text = (query or "").lower()
    triggers = ["add task", "create task", "new task", "remind me to", "add a task"]
    return any(trigger in text for trigger in triggers)


def parse_task_with_groq(query):
    system_prompt = (
        "You extract task fields from a user sentence. "
        "Return strict JSON only with keys: title, due_date, category. "
        "due_date must be YYYY-MM-DD or null. category must be short."
    )

    content, error = call_groq(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ],
        temperature=0,
    )
    if error:
        return None

    parsed = parse_json_from_text(content)
    if not isinstance(parsed, dict):
        return None

    title = (parsed.get("title") or "").strip()
    if not title:
        return None

    due_date = parsed.get("due_date")
    if due_date:
        try:
            datetime.strptime(due_date, "%Y-%m-%d")
        except ValueError:
            due_date = None

    category = normalize_category(parsed.get("category"))

    return {
        "title": title,
        "due_date": due_date,
        "category": category,
    }


def suggest_with_groq(query, tasks):
    summary = summarize_tasks_for_ai(tasks)

    system_prompt = (
        "You are the Flowboard assistant. Be concise, actionable, and practical. "
        "Use the task summary to answer the user question. "
        "Keep output under 120 words unless asked otherwise."
    )

    user_content = (
        f"User query: {query}\n"
        f"Task summary JSON: {json.dumps(summary)}"
    )

    content, error = call_groq(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        temperature=0.4,
    )
    if error:
        return (
            "AI suggestions are unavailable right now. "
            "Try again shortly, or ask for overdue/due-this-week summaries."
        )

    return content.strip()

@app.route("/tasks", methods=["GET"])
@jwt_required()
def get_tasks():
    session = Session()
    user_id = int(get_jwt_identity())
    category_filter = request.args.get("category")

    query = session.query(Task).filter_by(user_id=user_id)
    if category_filter and category_filter.strip().lower() != "all":
        normalized = category_filter.strip().lower()
        query = query.filter(func.lower(func.trim(Task.category)) == normalized)

    tasks = query.all()
    session.close()
    return jsonify([
        {
            "id": t.id,
            "title": t.title,
            "completed": t.completed,
            "due_date": t.due_date.strftime("%Y-%m-%d") if t.due_date else None,
            "category": t.category
        } for t in tasks
    ])


@app.route("/categories", methods=["GET"])
@jwt_required()
def get_categories():
    session = Session()
    user_id = int(get_jwt_identity())

    tasks = session.query(Task).filter_by(user_id=user_id).all()
    categories = sorted(
        {normalize_category(t.category) for t in tasks if (t.category or "").strip()},
        key=lambda item: item.lower(),
    )

    session.close()
    return jsonify(categories)

@app.route("/stats", methods=["GET"])
@jwt_required()
def stats():
    session = Session()
    user_id = int(get_jwt_identity())

    total = session.query(Task).filter_by(user_id=user_id).count()
    completed = session.query(Task).filter_by(user_id=user_id, completed=True).count()

    session.close()

    return jsonify({
        "total": total,
        "completed": completed,
        "completion_rate": completed / total if total else 0
    })
    

@app.route("/tasks", methods=["POST"])
@jwt_required()
def create_task():
    session = Session()
    user_id = int(get_jwt_identity())
    data = request.json

    due_date = data.get("due_date")

    task = Task(
        title=data["title"],
        completed=False,
        due_date=datetime.strptime(due_date, "%Y-%m-%d").date() if due_date else None,
        category=normalize_category(data.get("category")),
        user_id=user_id
    )

    session.add(task)
    session.commit()
    session.close()

    return jsonify({"msg": "Task created"})

@app.route("/tasks/<int:id>", methods=["PUT"])
@jwt_required()
def update_task(id):
    session = Session()
    user_id = int(get_jwt_identity())
    task = session.query(Task).filter_by(id=id, user_id=user_id).first()

    if not task:
        session.close()
        return jsonify({"message": "Task not found"}), 404

    data = request.json
    task.title = data.get("title", task.title)
    task.completed = data.get("completed", task.completed)
    if "due_date" in data:
        task.due_date = datetime.strptime(data["due_date"], "%Y-%m-%d").date() if data["due_date"] else None
    if "category" in data:
        task.category = normalize_category(data.get("category"))

    session.commit()
    session.close()
    return jsonify({"message": "Task updated"})


@app.route("/tasks/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_task(id):
    session = Session()
    user_id = int(get_jwt_identity())
    task = session.query(Task).filter_by(id=id, user_id=user_id).first()

    if not task:
        session.close()
        return jsonify({"message": "Task not found"}), 404

    session.delete(task)
    session.commit()
    session.close()
    return jsonify({"message": "Task deleted"})
    
@app.route("/")
def index():
    return jsonify({"message": "Backend is running! Go to /tasks to see the API."}), 200

@app.route("/register", methods=["POST"])
def register():
    session = Session()
    data = request.json

    existing_user = session.query(User).filter_by(username=data["username"]).first()
    if existing_user:
        session.close()
        return jsonify({"msg": "Username already exists"}), 400

    user = User(username=data["username"])
    user.set_password(data["password"])

    session.add(user)
    session.commit()
    session.close()

    return jsonify({"msg": "User created"})


@app.route("/login", methods=["POST"])
def login():
    session = Session()
    data = request.json

    user = session.query(User).filter_by(username=data["username"]).first()

    if user and user.check_password(data["password"]):
        token = create_access_token(identity=str(user.id))
        return jsonify({"access_token": token})

    return jsonify({"msg": "Invalid credentials"}), 401


@app.route("/ai-assistant", methods=["POST"])
@jwt_required()
def ai_assistant():
    session = Session()
    user_id = int(get_jwt_identity())
    data = request.json or {}
    query = (data.get("query") or "").strip()

    if not query:
        session.close()
        return jsonify({"msg": "Query is required"}), 400

    tasks = session.query(Task).filter_by(user_id=user_id).all()
    lowered = query.lower()

    if "due this week" in lowered:
        answer = build_due_this_week_response(tasks)
        session.close()
        return jsonify({"answer": answer})

    if "overdue" in lowered:
        answer = build_overdue_response(tasks)
        session.close()
        return jsonify({"answer": answer})

    if "completed" in lowered and "summary" in lowered:
        answer = build_completed_summary(tasks)
        session.close()
        return jsonify({"answer": answer})

    if looks_like_task_creation(query):
        parsed_task = parse_task_with_groq(query)
        session.close()

        if not parsed_task:
            return jsonify({
                "answer": "I could not confidently parse that task. Try: Add task Finish report by 2026-03-25 in Work.",
            })

        return jsonify({
            "answer": "I parsed this task. Review and confirm to create it.",
            "action": "preview_create_task",
            "preview": parsed_task,
        })

    answer = suggest_with_groq(query, tasks)
    session.close()
    return jsonify({"answer": answer})

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5001)),
        debug=True
    )

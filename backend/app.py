from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity
)
from models import Task, Session, User

app = Flask(__name__)

app.config["JWT_SECRET_KEY"] = "super-secret-key"
jwt = JWTManager(app)

CORS(app)
session = Session()

@app.route("/tasks", methods=["GET"])
@jwt_required()
def get_tasks():
    session = Session()
    user_id = int(get_jwt_identity())

    tasks = session.query(Task).filter_by(user_id=user_id).all()
    payload = [
        {
            "id": t.id,
            "title": t.title,
            "completed": t.completed,
            "due_date": t.due_date.isoformat() if t.due_date else None,
        }
        for t in tasks
    ]

    session.close()
    return jsonify(payload)

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

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)


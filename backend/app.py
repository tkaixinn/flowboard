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

    current_user_id = int(get_jwt_identity())

    session = Session()

    tasks = session.query(Task).filter_by(user_id=current_user_id).all()

    session.close()
    return jsonify([
        {"id": t.id, "title": t.title, "completed": t.completed}
        for t in tasks
    ])
    

@app.route("/tasks", methods=["POST"])
@jwt_required()
def create_task():
    session = Session()
    user_id = get_jwt_identity()

    data = request.json

    task = Task(
        title=data["title"],
        completed=False,
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
    current_user_id = int(get_jwt_identity())

    # Make sure user owns the task
    task = session.query(Task).filter_by(id=id, user_id=current_user_id).first()
    if task:
        data = request.json
        task.completed = data.get("completed", task.completed)
        task.title = data.get("title", task.title)
        session.commit()
        session.close()
        return jsonify({"message": "Task updated"})
    
    session.close()
    return jsonify({"message": "Task not found"}), 404


@app.route("/tasks/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_task(id):
    session = Session()
    current_user_id = int(get_jwt_identity())

    # Make sure user owns the task
    task = session.query(Task).filter_by(id=id, user_id=current_user_id).first()
    if task:
        session.delete(task)
        session.commit()
        session.close()
        return jsonify({"message": "Task deleted"})
    
    session.close()
    return jsonify({"message": "Task not found"}), 404

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


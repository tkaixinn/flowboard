from flask import Flask, jsonify, request
from flask_cors import CORS
from models import Task, Session

app = Flask(__name__)
CORS(app)
session = Session()

@app.route("/tasks", methods=["GET"])
def get_tasks():
    tasks = session.query(Task).all()
    return jsonify([{"id": t.id, "title": t.title, "completed": t.completed} for t in tasks])

@app.route("/tasks", methods=["POST"])
def add_task():
    data = request.json
    new_task = Task(title=data["title"], completed=False)
    session.add(new_task)
    session.commit()
    return jsonify({"message": "Task added"})

@app.route("/tasks/<int:id>", methods=["PUT"])
def update_task(id):
    data = request.json
    task = session.query(Task).get(id)
    if task:
        task.completed = data.get("completed", task.completed)
        task.title = data.get("title", task.title)
        session.commit()
        return jsonify({"message": "Task updated"})
    return jsonify({"message": "Task not found"}), 404

@app.route("/tasks/<int:id>", methods=["DELETE"])
def delete_task(id):
    task = session.query(Task).get(id)
    if task:
        session.delete(task)
        session.commit()
        return jsonify({"message": "Task deleted"})
    return jsonify({"message": "Task not found"}), 404

@app.route("/")
def index():
    return jsonify({"message": "Backend is running! Go to /tasks to see the API."}), 200

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)


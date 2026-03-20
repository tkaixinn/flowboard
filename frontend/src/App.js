import React, { useEffect, useState } from "react";
import axios from "axios";

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:5001";

function App() {
  const [tasks, setTasks] = useState([]);
  const [newTask, setNewTask] = useState("");
  const [error, setError] = useState("");

  const fetchTasks = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/tasks`);
      setTasks(res.data);
      setError("");
    } catch (err) {
      setError("Cannot reach backend API. Make sure backend is running on port 5001.");
    }
  };

  const addTask = async () => {
    if (!newTask.trim()) return;
    try {
      await axios.post(`${API_BASE_URL}/tasks`, { title: newTask });
      setNewTask("");
      fetchTasks();
    } catch (err) {
      setError("Failed to add task. Check backend connection.");
    }
  };

  const toggleComplete = async (task) => {
    try {
      await axios.put(`${API_BASE_URL}/tasks/${task.id}`, {
        completed: !task.completed,
      });
      fetchTasks();
    } catch (err) {
      setError("Failed to update task. Check backend connection.");
    }
  };

  const deleteTask = async (task) => {
    try {
      await axios.delete(`${API_BASE_URL}/tasks/${task.id}`);
      fetchTasks();
    } catch (err) {
      setError("Failed to delete task. Check backend connection.");
    }
  };

  useEffect(() => {
    fetchTasks();
  }, []);

  return (
    <div className="p-10 max-w-md mx-auto">
      <h1 className="text-2xl font-bold mb-4">Personal Dashboard</h1>
      {error && <p style={{ color: "#b91c1c", marginBottom: "12px" }}>{error}</p>}
      <div className="flex mb-4">
        <input
          value={newTask}
          onChange={(e) => setNewTask(e.target.value)}
          className="border p-2 flex-1"
          placeholder="New task"
        />
        <button onClick={addTask} className="bg-blue-500 text-white p-2 ml-2">
          Add
        </button>
      </div>
      <ul>
        {tasks.map((task) => (
          <li key={task.id} className="flex justify-between mb-2">
            <span
              className={task.completed ? "line-through" : ""}
              onClick={() => toggleComplete(task)}
            >
              {task.title}
            </span>
            <button onClick={() => deleteTask(task)} className="text-red-500">
              Delete
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default App;
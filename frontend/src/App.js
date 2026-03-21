import React, { useEffect, useState } from "react";
import axios from "axios";

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:5001";

function App() {
  const [tasks, setTasks] = useState([]);
  const [newTask, setNewTask] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [error, setError] = useState("");
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [isAuthPage, setIsAuthPage] = useState(!token);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [stats, setStats] = useState(null);

  const fetchTasks = async (authToken) => {
    try {
      const res = await axios.get(`${API_BASE_URL}/tasks`, {
        headers: { Authorization: `Bearer ${authToken}` }
      });
      setTasks(res.data);
      const statsRes = await axios.get(`${API_BASE_URL}/stats`, {
        headers: { Authorization: `Bearer ${authToken}` }
      });
      setStats(statsRes.data);
      setError("");
    } catch (err) {
      setError("Cannot reach backend API. Make sure backend is running on port 5001.");
    }
  };

  const handleRegister = async () => {
    if (!username.trim() || !password.trim()) {
      setError("Username and password are required");
      return;
    }
    try {
      const res = await axios.post(`${API_BASE_URL}/register`, {
        username,
        password
      });
      setError(res.data.msg);
      setUsername("");
      setPassword("");
    } catch (err) {
      setError(err.response?.data?.msg || "Registration failed");
    }
  };

  const handleLogin = async () => {
    if (!username.trim() || !password.trim()) {
      setError("Username and password are required");
      return;
    }
    try {
      const res = await axios.post(`${API_BASE_URL}/login`, {
        username,
        password
      });
      const newToken = res.data.access_token;
      setToken(newToken);
      localStorage.setItem("token", newToken);
      setIsAuthPage(false);
      setUsername("");
      setPassword("");
      setError("");
      fetchTasks(newToken);
    } catch (err) {
      setError(err.response?.data?.msg || "Login failed");
    }
  };

  const handleLogout = () => {
    setToken(null);
    setTasks([]);
    localStorage.removeItem("token");
    setIsAuthPage(true);
    setUsername("");
    setPassword("");
  };

  const addTask = async () => {
    if (!newTask.trim()) return;
    try {
      await axios.post(
        `${API_BASE_URL}/tasks`,
        { title: newTask, due_date: dueDate || null },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setNewTask("");
      setDueDate("");
      fetchTasks(token);
    } catch (err) {
      setError("Failed to add task.");
    }
  };

  const toggleComplete = async (task) => {
    try {
      await axios.put(`${API_BASE_URL}/tasks/${task.id}`, 
        { completed: !task.completed },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      fetchTasks(token);
    } catch (err) {
      setError("Failed to update task. Check backend connection.");
    }
  };

  const deleteTask = async (task) => {
    try {
      await axios.delete(`${API_BASE_URL}/tasks/${task.id}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      fetchTasks(token);
    } catch (err) {
      setError("Failed to delete task. Check backend connection.");
    }
  };

  useEffect(() => {
    if (token) {
      fetchTasks(token);
    }
  }, []);

  if (isAuthPage) {
    return (
      <div className="p-10 max-w-md mx-auto">
        <h1 className="text-2xl font-bold mb-4">Login / Register</h1>
        {error && <p style={{ color: "#b91c1c", marginBottom: "12px" }}>{error}</p>}
        <input
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="Username"
          className="border p-2 w-full mb-2"
        />
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password"
          className="border p-2 w-full mb-4"
        />
        <button onClick={handleLogin} className="bg-blue-500 text-white p-2 w-full mb-2">
          Login
        </button>
        <button onClick={handleRegister} className="bg-green-500 text-white p-2 w-full">
          Register
        </button>
      </div>
    );
  }

  return (
    <div className="p-10 max-w-md mx-auto">
      <h1 className="text-2xl font-bold mb-4">Personal Dashboard</h1>
      <button onClick={handleLogout} className="bg-red-500 text-white p-2 mb-4">
        Logout
      </button>
      {error && <p style={{ color: "#b91c1c", marginBottom: "12px" }}>{error}</p>}
      <div className="flex mb-4">
      <div className="flex flex-col flex-1">
        <input
          value={newTask}
          onChange={(e) => setNewTask(e.target.value)}
          className="border p-2 mb-2"
          placeholder="New task"
        />
        <input
          type="date"
          value={dueDate}
          onChange={(e) => setDueDate(e.target.value)}
          className="border p-2"
        />
      </div>
        <button onClick={addTask} className="bg-blue-500 text-white p-2 ml-2">
          Add
        </button>
      </div>
      {stats && (
        <div className="mb-4">
          <p>Total Tasks: {stats.total}</p>
          <p>Completed: {stats.completed}</p>
          <p>Completion Rate: {(stats.completion_rate * 100).toFixed(0)}%</p>
        </div>
      )}
      <ul>
        {tasks.map(task => {
          const isOverdue =
            task.due_date &&
            new Date(task.due_date) < new Date() &&
            !task.completed;

          return (
            <li key={task.id} className="flex justify-between items-center mb-2">
              <div className="flex items-center">
                <input
                  type="checkbox"
                  checked={task.completed}
                  onChange={() => toggleComplete(task)}
                  className="mr-2"
                />

                <div>
                  <strong
                    style={{
                      color: task.completed
                        ? "gray"
                        : isOverdue
                        ? "red"
                        : "black",
                      textDecoration: task.completed ? "line-through" : "none"
                    }}
                  >
                    {task.title}
                  </strong>

                  {task.due_date && (
                    <small className="block text-gray-500">
                      Due: {task.due_date}
                      {isOverdue && !task.completed && " (Overdue)"}
                    </small>
                  )}
                </div>
              </div>

              <button
                onClick={() => deleteTask(task)}
                className="text-red-500"
              >
                Delete
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export default App;
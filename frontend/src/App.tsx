import { useState, useEffect } from "react";
import Layout from "./components/Layout";
import Login from "./components/Login";

export default function App() {
  const [token, setToken] = useState<string | null>(
    () => localStorage.getItem("karl_token")
  );

  const handleLogin = (t: string) => {
    localStorage.setItem("karl_token", t);
    setToken(t);
  };

  const handleLogout = () => {
    localStorage.removeItem("karl_token");
    setToken(null);
  };

  if (!token) {
    return <Login onLogin={handleLogin} />;
  }

  return <Layout token={token} onLogout={handleLogout} />;
}

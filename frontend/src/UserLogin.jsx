import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import logo from './assets/logo.png';
import './Login.css';

function UserLogin() {
  const [universityId, setUniversityId] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');

    try {
      const response = await fetch('http://localhost:8000/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ university_id: universityId, name: name }),
      });

      if (!response.ok) throw new Error('فشل تسجيل الدخول. تأكد من صحة البيانات.');

      const data = await response.json();
      localStorage.setItem('user_session', data.session_token);
      localStorage.setItem('user_name', data.name);
      
      // Redirect to the chatbot
      navigate('/chat');
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="login-container" dir="rtl">
      <form className="login-box" onSubmit={handleLogin}>
        <div className="login-logo">
          <img src={logo} alt="المساعد الذكي" />
        </div>
        <h2>المساعد الذكي</h2>
        {error && <p className="error-text">{error}</p>}

        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="الاسم"
          required
        />

        <input
          type="text"
          value={universityId}
          onChange={(e) => setUniversityId(e.target.value)}
          placeholder="الرقم الجامعي او الحساب الجامعي"
          required
        />

        <button type="submit">تسجيل</button>
      </form>
    </div>
  );
}

export default UserLogin;
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

function AgentLogin() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');

    try {
      const response = await fetch('http://localhost:8000/agent/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email, password: password }),
      });

      if (!response.ok) throw new Error('البريد الإلكتروني أو كلمة المرور غير صحيحة');

      const data = await response.json();
      localStorage.setItem('agent_session', data.session_token);
      localStorage.setItem('agent_name', data.name);
      localStorage.setItem('agent_id', data.agent_id);
      
      // Redirect to the support dashboard
      navigate('/agent/dashboard');
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="login-container" dir="rtl">
      <form className="login-box agent-box" onSubmit={handleLogin}>
        <h2>بوابة الدعم الفني (Agents)</h2>
        {error && <p className="error-text">{error}</p>}
        
        <label>البريد الإلكتروني</label>
        <input 
          type="email" 
          value={email} 
          onChange={(e) => setEmail(e.target.value)} 
          required 
        />

        <label>كلمة المرور</label>
        <input 
          type="password" 
          value={password} 
          onChange={(e) => setPassword(e.target.value)} 
          required 
        />

        <button type="submit">تسجيل الدخول</button>
      </form>
    </div>
  );
}

export default AgentLogin;
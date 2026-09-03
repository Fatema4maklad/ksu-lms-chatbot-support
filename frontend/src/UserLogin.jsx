import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

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
        <h2>دخول المستفيدين (KSU)</h2>
        {error && <p className="error-text">{error}</p>}
        
        <label>الرقم الجامعي / الوظيفي</label>
        <input 
          type="text" 
          value={universityId} 
          onChange={(e) => setUniversityId(e.target.value)} 
          required 
        />

        <label>الاسم الكامل</label>
        <input 
          type="text" 
          value={name} 
          onChange={(e) => setName(e.target.value)} 
          required 
        />

        <button type="submit">بدء المحادثة</button>
      </form>
    </div>
  );
}

export default UserLogin;
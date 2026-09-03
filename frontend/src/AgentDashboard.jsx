import { useNavigate } from 'react-router-dom';

function AgentDashboard() {
  const navigate = useNavigate();
  const agentName = localStorage.getItem('agent_name');

  const handleLogout = () => {
    localStorage.removeItem('agent_session');
    localStorage.removeItem('agent_name');
    navigate('/agent/login');
  };

  return (
    <div dir="rtl" style={{ padding: '2rem' }}>
      <h1>لوحة تحكم الدعم الفني</h1>
      <p>مرحباً بك يا {agentName}</p>
      <button onClick={handleLogout} style={{ background: 'red', color: 'white' }}>تسجيل الخروج</button>
      {/* Table for active users/chats will go here later */}
    </div>
  );
}

export default AgentDashboard;
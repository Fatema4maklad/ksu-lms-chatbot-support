import { BrowserRouter, Routes, Route } from 'react-router-dom';
import UserLogin from './UserLogin';
import AgentLogin from './AgentLogin';
import ChatApp from './ChatApp';
import AgentDashboard from './AgentDashboard';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* User Routes */}
        <Route path="/" element={<UserLogin />} />
        <Route path="/chat" element={<ChatApp />} />
        
        {/* Agent Routes */}
        <Route path="/agent/login" element={<AgentLogin />} />
        <Route path="/agent/dashboard" element={<AgentDashboard />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
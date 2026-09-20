import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation, Navigate } from 'react-router-dom';
import { Mic, LayoutDashboard, MessageSquare } from 'lucide-react';
import { VoiceConsole } from './pages/VoiceConsole';
import { CommandCenter } from './pages/CommandCenter';
import { AnimatePresence, motion } from 'framer-motion';
import './App.css';

function AnimatedRoutes() {
  const location = useLocation();

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={location.pathname}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        transition={{ duration: 0.3 }}
        className="page-wrapper"
      >
        <Routes location={location}>
          <Route path="/" element={<Navigate to="/console" replace />} />
          <Route path="/console" element={<VoiceConsole />} />
          <Route path="/command-center" element={<CommandCenter />} />
          <Route path="/command center" element={<CommandCenter />} />
          <Route path="*" element={<Navigate to="/console" replace />} />
        </Routes>
      </motion.div>
    </AnimatePresence>
  );
}

export function Navigation({ onOpenHistory }: { onOpenHistory?: () => void }) {
  const location = useLocation();
  const isCommandCenter = location.pathname === '/command-center';

  return (
    <div className={`nav-container ${isCommandCenter ? 'in-sidebar' : 'floating'}`}>
      <nav className="app-nav">
        <Link to="/console" className={location.pathname === '/console' || location.pathname === '/' ? 'active' : ''}>
          <Mic size={15} className="nav-icon" /> User
        </Link>
        <Link to="/command-center" className={isCommandCenter ? 'active' : ''}>
          <LayoutDashboard size={15} className="nav-icon" /> Admin Panel
        </Link>
      </nav>
      {!isCommandCenter && (
        <button type="button" className="history-btn-standalone" onClick={onOpenHistory}>
          <MessageSquare size={14} color="#ff8c00" className="nav-icon" /> Recent Chats
        </button>
      )}
    </div>
  );
}

function App() {
  return (
    <Router>
      <div className="app-container">
        <AnimatedRoutes />
      </div>
    </Router>
  );
}

export default App;

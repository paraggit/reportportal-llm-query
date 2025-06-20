from typing import Dict, List, Optional
from datetime import datetime, timedelta
import uuid
import json
from pathlib import Path

from loguru import logger

from ..utils.config import Config


class SessionManager:
    """Manage user sessions and conversation history"""
    
    def __init__(self, config: Config):
        self.config = config
        self.sessions: Dict[str, Dict] = {}
        self.session_dir = Path(config.paths.session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.max_history_length = 50
        
    def create_session(self) -> str:
        """Create a new session"""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "created_at": datetime.now(),
            "last_active": datetime.now(),
            "history": []
        }
        logger.info(f"Created new session: {session_id}")
        return session_id
    
    def add_to_history(
        self, 
        session_id: str,
        query: str,
        response: str,
        metadata: Optional[dict] = None
    ):
        """Add query-response pair to session history"""
        if session_id not in self.sessions:
            logger.warning(f"Session {session_id} not found")
            return
        
        history_entry = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "response": response,
            "metadata": metadata
        }
        
        session = self.sessions[session_id]
        session["history"].append(history_entry)
        session["last_active"] = datetime.now()
        
        # Limit history length
        if len(session["history"]) > self.max_history_length:
            session["history"] = session["history"][-self.max_history_length:]
        
        # Persist to disk
        self._save_session(session_id)
    
    def get_session_history(self, session_id: str) -> Optional[List[Dict]]:
        """Get history for a session"""
        if session_id in self.sessions:
            return self.sessions[session_id]["history"]
        
        # Try loading from disk
        session = self._load_session(session_id)
        if session:
            self.sessions[session_id] = session
            return session["history"]
        
        return None
    
    def get_session_context(self, session_id: str, n_recent: int = 5) -> str:
        """Get recent conversation context for a session"""
        history = self.get_session_history(session_id)
        if not history:
            return ""
        
        recent_history = history[-n_recent:]
        context_parts = []
        
        for entry in recent_history:
            context_parts.append(f"User: {entry['query']}")
            context_parts.append(f"Assistant: {entry['response'][:200]}...")
        
        return "\n\n".join(context_parts)
    
    def close_session(self, session_id: str):
        """Close and save a session"""
        if session_id in self.sessions:
            self._save_session(session_id)
            del self.sessions[session_id]
            logger.info(f"Closed session: {session_id}")
    
    def cleanup_old_sessions(self, days: int = 7):
        """Remove sessions older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Clean in-memory sessions
        sessions_to_remove = []
        for session_id, session in self.sessions.items():
            if session["last_active"] < cutoff_date:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            del self.sessions[session_id]
        
        # Clean disk sessions
        for session_file in self.session_dir.glob("*.json"):
            try:
                if datetime.fromtimestamp(session_file.stat().st_mtime) < cutoff_date:
                    session_file.unlink()
            except Exception as e:
                logger.error(f"Error cleaning up session file {session_file}: {e}")
        
        logger.info(f"Cleaned up {len(sessions_to_remove)} old sessions")
    
    def _save_session(self, session_id: str):
        """Save session to disk"""
        if session_id not in self.sessions:
            return
        
        session_file = self.session_dir / f"{session_id}.json"
        
        # Convert datetime objects to strings
        session_data = self.sessions[session_id].copy()
        session_data["created_at"] = session_data["created_at"].isoformat()
        session_data["last_active"] = session_data["last_active"].isoformat()
        
        try:
            with open(session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving session {session_id}: {e}")
    
    def _load_session(self, session_id: str) -> Optional[Dict]:
        """Load session from disk"""
        session_file = self.session_dir / f"{session_id}.json"
        
        if not session_file.exists():
            return None
        
        try:
            with open(session_file, 'r') as f:
                session_data = json.load(f)
            
            # Convert strings back to datetime objects
            session_data["created_at"] = datetime.fromisoformat(session_data["created_at"])
            session_data["last_active"] = datetime.fromisoformat(session_data["last_active"])
            
            return session_data
        except Exception as e:
            logger.error(f"Error loading session {session_id}: {e}")
            return None

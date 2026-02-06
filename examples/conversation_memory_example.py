"""
Example: Conversation Memory Implementation
High-priority feature for multi-turn conversations
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

class ConversationMemory:
    """
    Persistent conversation memory with summarization
    Stores conversations in SQLite for cross-session memory
    """
    
    def __init__(self, db_path: str = "f1_agent_memory.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                timestamp TEXT,
                role TEXT,
                content TEXT,
                metadata TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_summaries (
                session_id TEXT PRIMARY KEY,
                summary TEXT,
                last_updated TEXT,
                message_count INTEGER
            )
        """)
        
        conn.commit()
        conn.close()
    
    def add_message(self, session_id: str, role: str, content: str, metadata: dict = None):
        """Add a message to conversation history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO conversations (session_id, timestamp, role, content, metadata)
            VALUES (?, ?, ?, ?, ?)
        """, (
            session_id,
            datetime.now().isoformat(),
            role,
            content,
            json.dumps(metadata or {})
        ))
        
        conn.commit()
        conn.close()
    
    def get_recent_messages(self, session_id: str, limit: int = 10) -> List[Dict]:
        """Get recent messages from a session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT role, content, timestamp, metadata
            FROM conversations
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (session_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "role": row[0],
                "content": row[1],
                "timestamp": row[2],
                "metadata": json.loads(row[3])
            }
            for row in reversed(rows)  # Reverse to chronological order
        ]
    
    def get_session_summary(self, session_id: str) -> str:
        """Get summary of previous session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT summary FROM session_summaries
            WHERE session_id = ?
        """, (session_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        return row[0] if row else None
    
    def save_session_summary(self, session_id: str, summary: str, message_count: int):
        """Save session summary"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO session_summaries 
            (session_id, summary, last_updated, message_count)
            VALUES (?, ?, ?, ?)
        """, (session_id, summary, datetime.now().isoformat(), message_count))
        
        conn.commit()
        conn.close()
    
    def summarize_session(self, session_id: str, llm) -> str:
        """Use LLM to summarize the conversation session"""
        messages = self.get_recent_messages(session_id, limit=50)
        
        if len(messages) < 3:
            return "New conversation"
        
        # Build conversation text
        convo_text = ""
        for msg in messages:
            convo_text += f"{msg['role']}: {msg['content']}\n"
        
        # Ask LLM to summarize
        summary_prompt = f"""Summarize this F1 conversation session in 2-3 sentences, focusing on:
1. Main topics discussed
2. Key decisions or insights
3. User's interests/preferences

Conversation:
{convo_text}

Summary:"""
        
        response = llm.invoke([HumanMessage(content=summary_prompt)])
        summary = response.content
        
        self.save_session_summary(session_id, summary, len(messages))
        return summary


# =============================================================================
# INTEGRATION WITH main.py
# =============================================================================

"""
# Add to main.py imports:
from conversation_memory import ConversationMemory
import uuid

# In main() function, before the loop:
session_id = str(uuid.uuid4())
memory = ConversationMemory()

# Load previous session summary if exists
previous_summary = memory.get_session_summary("last_session")
if previous_summary:
    console.print(f"[dim]Previous session: {previous_summary}[/dim]")
    
    # Optionally add to system prompt
    system_prompt_with_memory = SystemMessage(content=(
        f"{system_prompt.content}\n\n"
        f"PREVIOUS SESSION CONTEXT:\n{previous_summary}"
    ))
    chat_history = [system_prompt_with_memory]
else:
    chat_history = [system_prompt]

# In the main loop, after user input:
# Save user message
memory.add_message(session_id, "user", user_input)

# After getting AI response:
if final_response:
    memory.add_message(session_id, "assistant", final_response.content)
    chat_history.append(final_response)

# On exit (in except KeyboardInterrupt or normal exit):
console.print("\n[yellow]Saving conversation...[/yellow]")
summary = memory.summarize_session(session_id, llm)
memory.save_session_summary("last_session", summary, len(chat_history))
console.print(f"[green]Session saved: {summary}[/green]")
"""


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

if __name__ == "__main__":
    from langchain_ollama import ChatOllama
    
    # Initialize
    llm = ChatOllama(model="llama3.1", temperature=0)
    memory = ConversationMemory()
    
    # Simulate a conversation
    session_id = "test_session_123"
    
    memory.add_message(session_id, "user", "What are the 2026 regulation changes?")
    memory.add_message(session_id, "assistant", "The 2026 regulations include...")
    memory.add_message(session_id, "user", "How does this affect Red Bull?")
    memory.add_message(session_id, "assistant", "Red Bull will need to adapt...")
    
    # Retrieve conversation
    recent = memory.get_recent_messages(session_id, limit=5)
    print("\n=== Recent Messages ===")
    for msg in recent:
        print(f"{msg['role']}: {msg['content'][:50]}...")
    
    # Generate summary
    print("\n=== Generating Summary ===")
    summary = memory.summarize_session(session_id, llm)
    print(f"Summary: {summary}")
    
    # Load in new session
    print("\n=== Loading Previous Session ===")
    loaded_summary = memory.get_session_summary(session_id)
    print(f"Loaded: {loaded_summary}")


# =============================================================================
# BENEFITS
# =============================================================================
"""
1. User can ask follow-up questions without repeating context
   - "What about Ferrari?" (system remembers we were discussing 2026 regs)
   
2. Session continuity across restarts
   - Close agent, reopen tomorrow, it remembers your interests
   
3. Personalization over time
   - "Last time you asked about McLaren, here's an update..."
   
4. Better context for complex queries
   - Agent can reference previous questions/answers
   
5. Analytics on user interests
   - Track most asked topics
   - Customize proactive insights
"""

"""Conversation manager orchestrating the full streaming voice pipeline."""

from __future__ import annotations

import queue
import threading
import time
from enum import Enum
from typing import Any

from lily.event_bus import EventBus, EventTypes
from lily.intent_manager import IntentKinds, IntentManager
from lily.llm_manager import LLMManager
from lily.sentence_builder import SentenceBuilder
from lily.stt_manager import STTManager
from lily.tts_manager import TTSManager


class ConversationState(Enum):
    """States of the conversation flow."""
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"
    TOOL_EXECUTING = "tool_executing"


class ConversationManager:
    """Orchestrates the streaming conversational flow with interruption support."""

    def __init__(
        self,
        event_bus: EventBus,
        stt_manager: STTManager,
        intent_manager: IntentManager,
        llm_manager: LLMManager,
        tts_manager: TTSManager,
        sentence_builder: SentenceBuilder,
        memory=None,
        location_engine=None,
        hermes_agent=None,
    ):
        self.event_bus = event_bus
        self.stt = stt_manager
        self.intent = intent_manager
        self.llm = llm_manager
        self.tts = tts_manager
        self.sentence_builder = sentence_builder
        self.memory = memory
        self.location_engine = location_engine
        self.hermes = hermes_agent
        
        self._state = ConversationState.IDLE
        self._state_lock = threading.Lock()
        self._conversation_history: list[dict[str, str]] = []
        self._user_id = None
        self._user_name = "Guest"
        self._running = False
        
        # Subscribe to key events
        self._unsubs = [
            event_bus.subscribe(EventTypes.USER_STARTED_SPEAKING, self._on_user_started_speaking),
            event_bus.subscribe(EventTypes.USER_STOPPED_SPEAKING, self._on_user_stopped_speaking),
            event_bus.subscribe(EventTypes.TRANSCRIPT_READY, self._on_transcript_ready),
            event_bus.subscribe(EventTypes.TTS_INTERRUPTED, self._on_tts_interrupted),
            event_bus.subscribe(EventTypes.TOOL_FINISHED, self._on_tool_finished),
        ]

    def start(self, user_id: int, user_name: str):
        """Start the conversation manager."""
        self._running = True
        self._user_id = user_id
        self._user_name = user_name
        self._set_state(ConversationState.IDLE)
        print(f"[Conversation] Started for {user_name}")

    def close(self):
        """Stop and clean up."""
        self._running = False
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()

    def _set_state(self, new_state: ConversationState):
        """Update conversation state and publish event."""
        with self._state_lock:
            old_state = self._state
            self._state = new_state
        
        if old_state != new_state:
            self.event_bus.publish(EventTypes.STATE_CHANGED, {
                "old_state": old_state.value,
                "new_state": new_state.value,
            })
            print(f"[Conversation] {old_state.value} → {new_state.value}")

    def _on_user_started_speaking(self, event):
        """Handle user starting to speak."""
        with self._state_lock:
            current = self._state
        
        if current == ConversationState.SPEAKING:
            # Barge-in: stop TTS immediately
            self.tts.stop_speaking()
            self._set_state(ConversationState.INTERRUPTED)
            time.sleep(0.15)  # Brief pause for natural feel
        
        self._set_state(ConversationState.LISTENING)

    def _on_user_stopped_speaking(self, event):
        """Handle user stopping speech."""
        with self._state_lock:
            if self._state != ConversationState.LISTENING:
                return
        
        # Add brief pause before thinking (feels more natural)
        time.sleep(0.2)
        
        # Get final transcript
        transcript = self.stt.transcribe_final()
        if transcript:
            self.event_bus.publish(EventTypes.TRANSCRIPT_READY, {"text": transcript})

    def _on_transcript_ready(self, event):
        """Process complete transcript."""
        text = event.payload.get("text", "").strip()
        if not text:
            self._set_state(ConversationState.IDLE)
            return

        print(f"[You] {text}")
        self._set_state(ConversationState.THINKING)
        
        # Classify intent
        intent = self.intent.classify(text)
        
        if intent.kind == IntentKinds.TOOL:
            # Route to Hermes agent
            self._handle_tool_request(text)
        else:
            # Route to conversational LLM
            self._handle_conversation(text)

    def _handle_conversation(self, text: str):
        """Handle conversational query with streaming LLM."""
        # Build system prompt with context
        location = "unknown"
        if self.location_engine:
            location = self.location_engine.as_text(self._user_id)
        
        facts = []
        topics = []
        recalls = []
        if self.memory:
            # Get user facts
            fact_rows = self.memory.get_facts(self._user_id)
            facts = [f"{fact} ({cat})" for fact, cat in fact_rows[:5]]
            
            # Get recent topics and recalls
            topics = self.memory.get_recent_topics_text(self._user_id, 5)
            recalls = self.memory.get_recent_recalls_text(self._user_id, 3)
        
        system_prompt = self.llm.build_system_prompt(
            user_name=self._user_name,
            location=location,
            facts=facts,
            topics=topics,
            recalls=recalls,
        )
        
        # Start sentence builder
        self.sentence_builder.start()
        
        # Start speaking state
        self._set_state(ConversationState.SPEAKING)
        
        # Stream LLM response in background
        thread = threading.Thread(
            target=self._stream_llm_response,
            args=(text, system_prompt),
            daemon=True,
        )
        thread.start()

    def _stream_llm_response(self, prompt: str, system_prompt: str):
        """Stream LLM response (runs in background thread)."""
        try:
            full_response = []
            for chunk in self.llm.generate_stream(
                prompt=prompt,
                system_prompt=system_prompt,
                conversation_history=self._conversation_history,
            ):
                if "token" in chunk:
                    full_response.append(chunk["token"])
                elif "error" in chunk:
                    print(f"[LLM] Error: {chunk['error']}")
                    break
            
            # Store in conversation history
            response_text = "".join(full_response).strip()
            if response_text:
                self._conversation_history.append({"role": "user", "content": prompt})
                self._conversation_history.append({"role": "assistant", "content": response_text})
                
                # Store in memory
                if self.memory:
                    self.memory.add_message(self._user_id, "user", prompt)
                    self.memory.add_message(self._user_id, "assistant", response_text)
                    
                    # Extract facts in background
                    threading.Thread(
                        target=self._extract_facts,
                        args=(prompt, response_text),
                        daemon=True,
                    ).start()
            
            # Return to idle after speaking finishes
            # Wait a bit for TTS to complete
            time.sleep(0.5)
            with self._state_lock:
                if self._state == ConversationState.SPEAKING:
                    self._set_state(ConversationState.IDLE)
                    
        except Exception as e:
            print(f"[Conversation] Error streaming response: {e}")
            self._set_state(ConversationState.IDLE)

    def _extract_facts(self, user_text: str, assistant_text: str):
        """Extract and store facts from conversation (background task)."""
        if not self.memory:
            return
        
        # Use LLM to extract facts
        extraction_prompt = f"""Analyze this exchange:

User: "{user_text}"
Assistant: "{assistant_text}"

Extract any NEW facts about the user worth remembering long-term (name, preferences, 
projects, skills, goals, likes/dislikes). Ignore one-off requests.

Respond with ONLY a JSON array. If nothing to remember, respond exactly: []

Example: [{{"fact": "Working on AI project", "category": "projects"}}]
"""
        
        try:
            import json
            response = self.llm.generate_sync(
                prompt=extraction_prompt,
                options={"temperature": 0.3, "num_predict": 200},
            )
            
            # Parse JSON
            import re
            content = re.sub(r"^```(?:json)?|```$", "", response, flags=re.MULTILINE).strip()
            facts = json.loads(content)
            
            if isinstance(facts, list):
                for item in facts:
                    fact = str(item.get("fact", "")).strip()
                    category = str(item.get("category", "general")).strip() or "general"
                    if fact and not self.memory.fact_exists(self._user_id, fact):
                        self.memory.add_fact(self._user_id, fact, category)
                        print(f"[Memory] Learned: {fact} ({category})")
        except Exception as e:
            print(f"[Memory] Fact extraction skipped: {e}")

    def _handle_tool_request(self, text: str):
        """Handle tool/action request via Hermes agent."""
        if not self.hermes:
            # Fallback to conversation
            self._handle_conversation(f"I need to {text}")
            return
        
        self._set_state(ConversationState.TOOL_EXECUTING)
        
        # Show thinking cue
        self.event_bus.publish(EventTypes.LLM_SENTENCE, {
            "sentence": "Let me handle that..."
        })
        
        # Run agent in background
        thread = threading.Thread(
            target=self._execute_tool,
            args=(text,),
            daemon=True,
        )
        thread.start()

    def _execute_tool(self, goal: str):
        """Execute tool request via Hermes (background thread)."""
        try:
            result = self.hermes.run(goal=goal, max_steps=5)
            
            # Announce result
            if result.status.value == "completed":
                message = f"Done. {result.message[:200]}"
            else:
                message = f"I had some trouble: {result.message[:200]}"
            
            self.event_bus.publish(EventTypes.TOOL_FINISHED, {
                "goal": goal,
                "status": result.status.value,
                "message": message,
            })
            
        except Exception as e:
            print(f"[Tool] Execution error: {e}")
            self.event_bus.publish(EventTypes.TOOL_FINISHED, {
                "goal": goal,
                "status": "failed",
                "message": f"Error: {e}",
            })

    def _on_tool_finished(self, event):
        """Handle tool execution completion."""
        message = event.payload.get("message", "Task complete")
        
        # Speak result
        self.event_bus.publish(EventTypes.LLM_SENTENCE, {"sentence": message})
        
        time.sleep(0.5)
        self._set_state(ConversationState.IDLE)

    def _on_tts_interrupted(self, event):
        """Handle TTS interruption."""
        reason = event.payload.get("reason", "unknown")
        print(f"[Conversation] TTS interrupted: {reason}")

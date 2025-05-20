# ai_notes.py
"""
AI-powered note generation for Zoom meetings.
This module generates structured notes and summaries from meeting transcripts.
"""

import os
import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MeetingNote:
    """Structure for a meeting note."""
    timestamp: str
    content: str
    tags: List[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp,
            "content": self.content,
            "tags": self.tags or []
        }

@dataclass
class ActionItem:
    """Structure for an action item extracted from a meeting."""
    description: str
    assigned_to: str = None
    due_date: str = None
    priority: str = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "description": self.description,
            "assigned_to": self.assigned_to,
            "due_date": self.due_date,
            "priority": self.priority
        }

@dataclass
class MeetingSummary:
    """Comprehensive summary of a meeting."""
    meeting_id: str
    date: str
    title: str = None
    summary: str = None
    key_points: List[str] = None
    action_items: List[ActionItem] = None
    notes: List[MeetingNote] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "meeting_id": self.meeting_id,
            "date": self.date,
            "title": self.title or "Untitled Meeting",
            "summary": self.summary or "",
            "key_points": self.key_points or [],
            "action_items": [ai.to_dict() for ai in (self.action_items or [])],
            "notes": [note.to_dict() for note in (self.notes or [])]
        }
    
    def save(self, file_path: str) -> None:
        """Save meeting summary to JSON file."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
            logger.info(f"Saved meeting summary to {file_path}")
        except Exception as e:
            logger.error(f"Error saving meeting summary: {str(e)}")

class AINotesGenerator:
    """Generates AI-powered notes from meeting transcripts."""
    
    def __init__(self, use_llama: bool = True):
        """
        Initialize the AI notes generator.
        
        Args:
            use_llama: Whether to use local LLaMA model or OpenAI API
        """
        self.use_llama = use_llama
        
        if use_llama:
            try:
                from openai import OpenAI
                import config
                self.client = OpenAI(base_url=config.LLAMA_HOST, api_key="ollama")
                logger.info("Using LLaMA for AI notes generation")
            except ImportError:
                logger.warning("OpenAI client not available for LLaMA, using simple notes")
                self.client = None
        else:
            try:
                import openai
                self.client = openai.Client(api_key=os.environ.get("OPENAI_API_KEY"))
                logger.info("Using OpenAI for AI notes generation")
            except ImportError:
                logger.warning("OpenAI client not available, using simple notes")
                self.client = None
    
    def generate_note(self, transcript_segment: str) -> MeetingNote:
        """
        Generate a note from a transcript segment.
        
        Args:
            transcript_segment: The transcript text to analyze
            
        Returns:
            A MeetingNote object
        """
        if not transcript_segment:
            return MeetingNote(
                timestamp=datetime.now().strftime("%H:%M:%S"),
                content="Empty transcript segment",
                tags=["error"]
            )
        
        try:
            if self.client:
                # Use LLM to generate note
                prompt = f"""
                Create a concise and informative note from this meeting transcript segment.
                Extract key points, decisions, or action items if present.
                Also suggest up to 3 relevant tags for categorization.
                
                Transcript segment:
                {transcript_segment}
                
                Return only the note content followed by tags in JSON format:
                {{
                  "note": "The concise note text here",
                  "tags": ["tag1", "tag2", "tag3"]
                }}
                """
                
                if self.use_llama:
                    # Use LLaMA
                    response = self.client.chat.completions.create(
                        model="llama3.2",
                        messages=[
                            {"role": "system", "content": "You are a meeting assistant that creates concise notes from transcripts."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.3,
                        max_tokens=300
                    )
                    content = response.choices[0].message.content
                else:
                    # Use OpenAI
                    response = self.client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are a meeting assistant that creates concise notes from transcripts."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.3,
                        max_tokens=300
                    )
                    content = response.choices[0].message.content
                
                # Parse JSON response
                try:
                    # Extract JSON from the response
                    import re
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                        data = json.loads(json_str)
                        return MeetingNote(
                            timestamp=datetime.now().strftime("%H:%M:%S"),
                            content=data.get("note", "No note content"),
                            tags=data.get("tags", [])
                        )
                except Exception as e:
                    logger.error(f"Error parsing AI response: {str(e)}")
            
            # Fallback to simple note generation
            words = transcript_segment.split()
            truncated = " ".join(words[:30]) + ("..." if len(words) > 30 else "")
            return MeetingNote(
                timestamp=datetime.now().strftime("%H:%M:%S"),
                content=f"Meeting discussion: {truncated}",
                tags=["transcript"]
            )
            
        except Exception as e:
            logger.error(f"Error generating note: {str(e)}")
            return MeetingNote(
                timestamp=datetime.now().strftime("%H:%M:%S"),
                content=f"Error generating note: {str(e)}",
                tags=["error"]
            )
    
    def extract_action_items(self, transcript: str) -> List[ActionItem]:
        """
        Extract action items from a transcript.
        
        Args:
            transcript: The full transcript text
            
        Returns:
            List of ActionItem objects
        """
        if not transcript or len(transcript) < 100:
            return []
        
        try:
            if self.client:
                # Use LLM to extract action items
                prompt = f"""
                Extract all action items, tasks, and assignments from this meeting transcript.
                For each action item, identify:
                1. The task description
                2. Who it's assigned to (if mentioned)
                3. Due date (if mentioned)
                4. Priority (if mentioned)
                
                Transcript:
                {transcript[:4000]}  # Limit length to avoid token limits
                
                Return the action items in JSON format:
                {{
                  "action_items": [
                    {{
                      "description": "The task to be done",
                      "assigned_to": "Person name or null",
                      "due_date": "Date or null",
                      "priority": "high/medium/low or null"
                    }},
                    ...
                  ]
                }}
                """
                
                if self.use_llama:
                    # Use LLaMA
                    response = self.client.chat.completions.create(
                        model="llama3.2",
                        messages=[
                            {"role": "system", "content": "You are a meeting assistant that extracts action items from transcripts."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.2,
                        max_tokens=1000
                    )
                    content = response.choices[0].message.content
                else:
                    # Use OpenAI
                    response = self.client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are a meeting assistant that extracts action items from transcripts."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.2,
                        max_tokens=1000
                    )
                    content = response.choices[0].message.content
                
                # Parse JSON response
                try:
                    import re
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                        data = json.loads(json_str)
                        
                        action_items = []
                        for item in data.get("action_items", []):
                            action_items.append(ActionItem(
                                description=item.get("description", "Unknown task"),
                                assigned_to=item.get("assigned_to"),
                                due_date=item.get("due_date"),
                                priority=item.get("priority")
                            ))
                        return action_items
                except Exception as e:
                    logger.error(f"Error parsing action items: {str(e)}")
            
            # Simple fallback extraction
            action_items = []
            lines = transcript.split("\n")
            for line in lines:
                if any(kw in line.lower() for kw in ["action", "task", "todo", "to-do", "to do", "will do", "assigned"]):
                    action_items.append(ActionItem(description=line.strip()))
            
            return action_items
            
        except Exception as e:
            logger.error(f"Error extracting action items: {str(e)}")
            return []
    
    def generate_meeting_summary(self, meeting_id: str, transcript: str) -> MeetingSummary:
        """
        Generate a comprehensive meeting summary from the transcript.
        
        Args:
            meeting_id: Unique identifier for the meeting
            transcript: The complete meeting transcript
            
        Returns:
            A MeetingSummary object
        """
        if not transcript:
            return MeetingSummary(
                meeting_id=meeting_id,
                date=datetime.now().strftime("%Y-%m-%d"),
                title="Empty Meeting",
                summary="No transcript available for this meeting."
            )
        
        try:
            # Extract action items
            action_items = self.extract_action_items(transcript)
            
            # Generate note segments
            notes = []
            # Split transcript into chunks for note generation
            if len(transcript) > 500:
                chunks = self._split_transcript(transcript)
                for i, chunk in enumerate(chunks):
                    if i % 3 == 0:  # Process every third chunk to reduce processing
                        note = self.generate_note(chunk)
                        notes.append(note)
            else:
                note = self.generate_note(transcript)
                notes.append(note)
            
            # Generate overall summary using LLM
            if self.client:
                prompt = f"""
                Create a concise summary of this meeting transcript. Include:
                1. A descriptive title for the meeting
                2. A 2-3 sentence summary of the discussion
                3. 3-5 key points or takeaways
                
                Transcript:
                {transcript[:4000]}  # Limit length to avoid token limits
                
                Return the summary in JSON format:
                {{
                  "title": "Meeting title",
                  "summary": "Brief summary of the discussion",
                  "key_points": ["Key point 1", "Key point 2", "Key point 3"]
                }}
                """
                
                if self.use_llama:
                    # Use LLaMA
                    response = self.client.chat.completions.create(
                        model="llama3.2",
                        messages=[
                            {"role": "system", "content": "You are a meeting assistant that creates concise summaries from transcripts."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.3,
                        max_tokens=800
                    )
                    content = response.choices[0].message.content
                else:
                    # Use OpenAI
                    response = self.client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are a meeting assistant that creates concise summaries from transcripts."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.3,
                        max_tokens=800
                    )
                    content = response.choices[0].message.content
                
                try:
                    import re
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                        data = json.loads(json_str)
                        
                        return MeetingSummary(
                            meeting_id=meeting_id,
                            date=datetime.now().strftime("%Y-%m-%d"),
                            title=data.get("title", "Meeting Summary"),
                            summary=data.get("summary", ""),
                            key_points=data.get("key_points", []),
                            action_items=action_items,
                            notes=notes
                        )
                except Exception as e:
                    logger.error(f"Error parsing summary: {str(e)}")
            
            # Simple fallback summary
            word_count = len(transcript.split())
            
            return MeetingSummary(
                meeting_id=meeting_id,
                date=datetime.now().strftime("%Y-%m-%d"),
                title=f"Meeting {meeting_id}",
                summary=f"This meeting had approximately {word_count} words of discussion.",
                key_points=["Automated summary not available"],
                action_items=action_items,
                notes=notes
            )
            
        except Exception as e:
            logger.error(f"Error generating meeting summary: {str(e)}")
            return MeetingSummary(
                meeting_id=meeting_id,
                date=datetime.now().strftime("%Y-%m-%d"),
                title=f"Meeting {meeting_id}",
                summary=f"Error generating summary: {str(e)}",
                action_items=[],
                notes=[]
            )
    
    def _split_transcript(self, transcript: str, chunk_size: int = 500) -> List[str]:
        """Split transcript into manageable chunks for processing."""
        words = transcript.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i+chunk_size])
            chunks.append(chunk)
        
        return chunks

#poll_prompt.py
import os
import json
import requests
import logging
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

POLL_PROMPT = """
You are an expert meeting assistant tasked with creating a poll based SOLELY on the provided meeting transcript. The poll must be 100% relevant to the transcript and ONLY contain information directly from the transcript.

##CRITICAL REQUIREMENTS##
- EVERY element of the poll MUST come directly from the transcript
- If the transcript doesn't have 4 distinct points, create a poll about the CENTRAL TOPIC instead with options about different aspects discussed
- NEVER create options that weren't explicitly mentioned in the transcript
- Poll must reflect ACTUAL discussion points, not hypothetical ones
- The question must address a SPECIFIC issue/topic from the transcript, not a generic one
- Title must directly relate to the main subject being discussed

##TRANSCRIPT ANALYSIS PROCESS##
1. First, identify the CENTRAL TOPIC of discussion - what is being primarily discussed?
2. Next, look for POINTS OF DECISION or DIFFERENT PERSPECTIVES on this topic
3. Note any specific OPTIONS, ALTERNATIVES, or APPROACHES mentioned
4. Identify any VARYING OPINIONS or PREFERENCES expressed by participants
5. Look for any QUANTITATIVE DATA mentioned (e.g., timelines, percentages, metrics)
6. Pay attention to SPECIFIC QUESTIONS asked by participants that received multiple responses

##POLL CREATION GUIDELINES##
- TITLE: Create a specific, engaging title that clearly identifies the exact topic from the transcript
- QUESTION: Formulate a focused question about a specific decision point or area of discussion from the transcript
- OPTIONS: Extract 4 distinct alternatives/perspectives that were ACTUALLY mentioned in the transcript

##QUALITY CHECKS##
- Re-read the transcript after creating the poll to verify every element is directly traceable to transcript text
- Confirm options are mutually exclusive when possible
- Verify the question directly connects to the most important decision point or topic
- Ensure the poll would make sense to meeting participants as a follow-up

##OUTPUT FORMAT##
Return a JSON object with this exact structure:
{
  "title": "Specific title about the central topic",
  "question": "Focused question about a key decision point?",
  "options": ["Option from transcript 1", "Option from transcript 2", "Option from transcript 3", "Option from transcript 4"]
}

Transcript:
[Insert transcript here]
"""

def generate_poll(transcript: str) -> Dict[str, Any]:
    """
    Generate a poll based on the provided transcript using LLaMA API.
    
    Args:
        transcript: The transcript text to generate a poll from
        
    Returns:
        Dict containing the poll with title, question, and options
    """
    try:
        # Default fallback poll in case of errors
        default_poll = {
            "title": "Error: Poll Generation Failed",
            "questions": [
                {
                    "name": "What should we discuss in the next meeting?",
                    "type": "single",
                    "answers": [
                        "Topic A", 
                        "Topic B", 
                        "Topic C", 
                        "Something else"
                    ]
                }
            ]
        }
        
        # Check environment variables for LLaMA host
        llama_host = os.environ.get("LLAMA_HOST", "http://localhost:11434")
        
        # Create prompt with transcript
        prompt = POLL_PROMPT.replace("[Insert transcript here]", transcript)
        
        # Call LLaMA API
        headers = {"Content-Type": "application/json"}
        data = {
            "model": "llama3.2",
            "prompt": prompt,
            "temperature": 0.2,  # Lower temperature for more focused, accurate responses
            "stream": False
        }
        
        response = requests.post(f"{llama_host}/api/generate", json=data, headers=headers)
        
        if response.status_code == 200:
            try:
                result = response.json()
                poll_json = json.loads(result.get('response', '{}'))
                
                # Format the poll as expected by the application
                formatted_poll = {
                    "title": poll_json.get("title", "Meeting Poll"),
                    "questions": [
                        {
                            "name": poll_json.get("question", "What do you think?"),
                            "type": "single",
                            "answers": poll_json.get("options", ["Option 1", "Option 2", "Option 3", "Option 4"])
                        }
                    ]
                }
                
                logger.info("Poll generated successfully")
                return formatted_poll
                
            except json.JSONDecodeError:
                logger.error("Failed to parse LLaMA response as JSON")
                return default_poll
                
        else:
            logger.error(f"LLaMA API returned status code {response.status_code}")
            return default_poll
            
    except Exception as e:
        logger.error(f"Error generating poll: {str(e)}")
        return default_poll
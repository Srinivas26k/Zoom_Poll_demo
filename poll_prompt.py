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
You are an expert meeting assistant tasked with creating a highly accurate and relevant poll based solely on the provided meeting transcript. Your objective is to generate a poll consisting of an eye-catching title, a specific question tied to the discussion, and exactly four distinct options, all derived directly from the transcript's content. The poll must reflect the key points, opinions, or decisions discussed, ensuring 100% relevance to the transcript without introducing external information or assumptions.

CRITICAL REQUIREMENTS:
1. EVERY element of the poll MUST be directly derived from the transcript content
2. NO assumptions or external knowledge should be used
3. If the transcript is unclear or too short, indicate this in the title
4. All options MUST be actual points or statements from the transcript
5. The question MUST be about a specific topic discussed in the transcript

Follow these steps to generate the poll:

1. **Transcript Analysis**:
   - Carefully read and analyze the entire transcript to understand its context, main topic, and key points.
   - Identify the central theme or focus of the discussion (e.g., a decision to be made, a topic debated, or a key insight).
   - Note any explicit statements, opinions, suggestions, or perspectives expressed by participants.
   - If the transcript is unclear or too short, note this for the title.

2. **Title Generation**:
   - Create a concise, engaging, and professional title that captures the essence of the discussion.
   - Make the title eye-catching by highlighting the most interesting or significant aspect of the transcript.
   - If the transcript is unclear or too short, include this in the title (e.g., "Clarification Needed: [Topic]").
   - Ensure the title is directly inspired by the transcript's content.

3. **Question Formulation**:
   - Formulate a clear and specific question that prompts participants to reflect on a significant aspect of the meeting.
   - The question MUST be about a specific topic discussed in the transcript.
   - Avoid generic questions; the question must be uniquely tied to the discussion.
   - If the transcript is unclear, ask for clarification about the main topic.

4. **Options Creation**:
   - Select or summarize exactly four distinct statements, opinions, or perspectives from the transcript.
   - Use direct quotes where possible, or create close paraphrases that preserve the original meaning.
   - Each option MUST be derived from actual content in the transcript.
   - If the transcript contains fewer than four distinct points, indicate this in the title and create options that reflect the available content.

5. **Validation Steps**:
   - Verify that every element (title, question, options) is directly from the transcript.
   - Check that no external knowledge or assumptions were used.
   - Ensure the poll makes sense in the context of the transcript.
   - If any element cannot be directly derived from the transcript, indicate this in the title.

6. **Output Format**:
   - Provide the poll in the following JSON format ONLY:
     {
       "title": "Engaging Title",
       "question": "Specific Question?",
       "options": ["Statement 1", "Statement 2", "Statement 3", "Statement 4"]
     }
   - Do not include any additional explanation or text outside of this JSON structure.

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
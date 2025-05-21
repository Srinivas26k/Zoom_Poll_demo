#poller.py
import json
import requests
import re
from openai import OpenAI
from rich.console import Console
import config
from poll_prompt import POLL_PROMPT
import os
import logging
from typing import Dict, List, Any, Optional
from typing_extensions import TypedDict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("poller")

console = Console()
if not hasattr(config, "LLAMA_HOST"):
    config.setup_config()
llama = OpenAI(base_url=config.LLAMA_HOST, api_key="ollama")

# Define the post_poll_to_meeting function directly instead of importing it
def post_poll_to_meeting(meeting_id: str, poll_data: Dict[str, Any], token: str) -> Optional[Dict[str, Any]]:
    """
    Post a poll to a Zoom meeting using the Zoom API.
    
    Args:
        meeting_id (str): Zoom meeting ID
        poll_data (Dict[str, Any]): Poll data to post
        token (str): Zoom API access token
        
    Returns:
        Optional[Dict[str, Any]]: Response data or None if request failed
    """
    url = f"https://api.zoom.us/v2/meetings/{meeting_id}/polls"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, headers=headers, json=poll_data, timeout=30)
        if response.status_code in (200, 201):
            return response.json()
        else:
            logger.error(f"Zoom API error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error posting poll to Zoom meeting: {str(e)}")
        return None

def extract_json_from_text(text):
    """
    Extracts JSON from text that might contain markdown or other text.
    
    Args:
        text (str): Text containing JSON (possibly with other content)
    
    Returns:
        dict: Parsed JSON object or None if not found
    """
    # Try to find JSON with regex pattern matching
    json_pattern = r'\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\}'
    match = re.search(json_pattern, text)
    
    if match:
        try:
            json_str = match.group(0)
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    
    return None

def generate_poll_from_transcript(transcript: str) -> tuple[Optional[str], Optional[str], Optional[list[str]]]:
    """
    Generate a poll from a transcript using LLaMA and the imported prompt.

    Args:
        transcript (str): The meeting transcript to analyze.

    Returns:
        tuple: (title, question, options) of the generated poll, or (None, None, None) if no poll can be generated.
    """
    # Clean and prepare the transcript
    clean_transcript = transcript.strip()
    if not clean_transcript or len(clean_transcript.split()) < 10:  # Ensure at least a few words
        console.log("[yellow]⚠️ Transcript too short or empty. No poll will be generated.[/]")
        return None, None, None
    
    # Combine the prompt with the transcript
    full_prompt = POLL_PROMPT.replace("[Insert transcript here]", clean_transcript)
    console.log("🤖 Generating poll from transcript…")
    console.log(f"📝 Transcript length: {len(clean_transcript)} characters")

    try:
        # Request poll from LLaMA with higher temperature for more creative options
        # but lower max_tokens to focus the response
        resp = llama.chat.completions.create(
            model="llama3.2:latest",
            messages=[{"role": "user", "content": full_prompt}],
            temperature=0.7,
            max_tokens=800,  # Increased to allow for complete responses
            response_format={"type": "json_object"}  # Request JSON response
        )
        raw_response = resp.choices[0].message.content.strip()
        console.log(f"📥 LLaMA raw response received ({len(raw_response)} chars)")
        
        # Try to extract JSON from the response
        poll_data = extract_json_from_text(raw_response)
        
        # If we couldn't extract JSON with regex, fall back to direct parsing
        if poll_data is None:
            try:
                poll_data = json.loads(raw_response)
            except json.JSONDecodeError as e:
                console.log(f"[yellow]⚠️ JSON parsing error:[/] {e}")
                console.log(f"Raw response: {raw_response[:100]}...")
                raise

        # Extract and validate components
        title = poll_data.get("title")
        question = poll_data.get("question")
        options = poll_data.get("options", [])
        
        # Validate title and question
        if not title or not isinstance(title, str):
            console.log("[yellow]⚠️ Invalid or missing title, using default[/]")
            title = "Meeting Poll"
        
        if not question or not isinstance(question, str):
            console.log("[yellow]⚠️ Invalid or missing question, using default[/]")
            question = "What was the main topic discussed?"
        
        # Validate and adjust options to ensure exactly 4
        if not isinstance(options, list):
            console.log("[yellow]⚠️ Options are not a list, creating defaults[/]")
            options = []
            
        # Make sure we have exactly 4 options
        if len(options) > 4:
            console.log(f"[yellow]⚠️ Too many options ({len(options)}), truncating to 4[/]")
            options = options[:4]
            
        while len(options) < 4:
            if len(options) == 0:
                # If we have no options at all, create generic ones
                default_options = [
                    "Option 1 (from transcript)",
                    "Option 2 (from transcript)",
                    "Option 3 (from transcript)",
                    "Option 4 (from transcript)"
                ]
                options.extend(default_options[:4-len(options)])
            else:
                # If we have some options but not enough, create numbered extras
                options.append(f"Additional point from discussion {len(options) + 1}")
        
        # Log success
        console.log(f"[green]✅ Successfully generated poll:[/]")
        console.log(f"Title: {title}")
        console.log(f"Question: {question}")
        console.log(f"Options: {options}")
        
        return title, question, options

    except Exception as e:
        console.log(f"[red]❌ Poll generation error:[/] {e}")
        
        # Create a fallback poll that indicates there was an error
        fallback_title = "Meeting Discussion Poll"
        fallback_question = "What topic should we focus on next?"
        fallback_options = [
            "Continue current discussion",
            "Move to next agenda item",
            "Take questions from participants",
            "Summarize key points so far"
        ]
        
        return fallback_title, fallback_question, fallback_options

def launch_poll(meeting_id: str, poll_id: str, token: str) -> bool:
    """
    Launch a poll in a Zoom meeting.

    Args:
        meeting_id (str): Zoom meeting ID.
        poll_id (str): ID of the poll to launch.
        token (str): Zoom API token.

    Returns:
        bool: True if successful, False otherwise.
    """
    url = f"https://api.zoom.us/v2/meetings/{meeting_id}/polls/{poll_id}/launch"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, headers=headers)
        if response.status_code == 200:
            console.log(f"[green]✅ Poll launched successfully[/]")
            return True
        else:
            console.log(f"[red]❌ Failed to launch poll[/]: {response.status_code} {response.text}")
            return False
    except Exception as e:
        console.log(f"[red]❌ Poll launch error[/]: {e}")
        return False

def post_poll_to_zoom(title: str, question: str, options: list[str], meeting_id: str, token: str) -> bool:
    """
    Post a poll to a Zoom meeting using the Zoom API.

    Args:
        title (str): Poll title.
        question (str): Poll question.
        options (list[str]): List of four poll options.
        meeting_id (str): Zoom meeting ID.
        token (str): Zoom API token.

    Returns:
        bool: True if successful, False otherwise.
    """
    url = f"https://api.zoom.us/v2/meetings/{meeting_id}/polls"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Make sure we have exactly 4 options
    if len(options) > 4:
        options = options[:4]
    while len(options) < 4:
        options.append(f"Option {len(options) + 1}")
    
    payload = {
        "title": title,
        "questions": [{
            "name": question,
            "type": "single",
            "answer_required": True,
            "answers": options
        }]
    }

    console.log(f"📤 Posting poll to Zoom: {title} - {question}")
    console.log(f"Options: {options}")

    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 201:
            poll_data = response.json()
            console.log(f"[green]✅ Poll posted successfully[/]: {poll_data}")
            
            # For meetings, the poll must be launched manually by the host in the Zoom client.
            console.log("[yellow]Poll created. Please launch it manually from the Zoom client.[/]")
            return True
        else:
            console.log(f"[red]❌ Zoom API error[/]: {response.status_code} {response.text}")
            return False
    except Exception as e:
        console.log(f"[red]❌ Poll posting error[/]: {e}")
        return False

def is_meaningful_text(text: str) -> bool:
    """Check if the transcription contains enough meaningful content"""
    # Remove spaces and check if we have at least 20 characters
    cleaned_text = text.strip()
    if len(cleaned_text) < 20:
        return False
    
    # Check if there are at least 4 meaningful words
    words = [w for w in re.split(r'\W+', cleaned_text) if len(w) > 1]
    return len(words) >= 4

def clean_text(text: str) -> str:
    """Clean up transcription text for better poll generation"""
    # Remove excessive spaces and newlines
    cleaned = re.sub(r'\s+', ' ', text).strip()
    # Remove common speech artifacts
    cleaned = re.sub(r'\b(um|uh|like|you know|I mean)\b', '', cleaned, flags=re.IGNORECASE)
    return cleaned

def generate_poll_with_llama(transcription: str) -> Optional[Dict[str, Any]]:
    """Generate a poll based on the meeting transcription using Llama API"""
    if not is_meaningful_text(transcription):
        logger.warning("Transcription doesn't contain enough meaningful content for a poll")
        return None
    
    # Clean the transcription
    cleaned_text = clean_text(transcription)
    
    # Extract key topics and themes
    topics = extract_key_topics(cleaned_text)
    if not topics:
        topics = "the current discussion"
    
    # Create a structured prompt for the LLM
    prompt = f"""You are an AI assistant that creates relevant polls for Zoom meetings.

MEETING TRANSCRIPT:
---
{cleaned_text}
---

KEY TOPICS FROM TRANSCRIPT: {topics}

Create ONE poll question with exactly 4 answer options based STRICTLY on the actual content of the meeting transcript above.
The poll must ONLY address topics that were explicitly discussed in the transcript.
DO NOT introduce new topics or concepts not mentioned in the transcript.

IMPORTANT RULES:
1. The poll MUST be directly related to the main topic discussed in the transcript
2. All options MUST be derived from actual statements or points made in the transcript
3. Do not make up or assume any content not present in the transcript
4. If the transcript is unclear or too short, indicate this in the title

Your response should be in this JSON format with no other text:
{{
  "title": "Brief descriptive title",
  "question": "A clear question about a specific topic from the transcript?",
  "options": ["Option 1", "Option 2", "Option 3", "Option 4"]
}}

Make sure the question and options are directly related to the content in the transcript.
"""
    
    # Prepare the request
    headers = {
        "Content-Type": "application/json"
    }
    
    # Check if we're using local or remote Llama
    if hasattr(config, "LLAMA_HOST") and config.LLAMA_HOST:
        try:
            # Local Ollama setup
            url = f"{config.LLAMA_HOST}/api/generate"
            data = {
                "model": "llama3.2",
                "prompt": prompt,
                "temperature": 0.7,
                "max_tokens": 500
            }
            
            logger.info(f"Requesting poll from LLaMA at {url}")
            logger.info(f"Transcript length: {len(cleaned_text)} characters")
            logger.info(f"Key topics identified: {topics}")
            
            response = requests.post(url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            raw_text = result.get('response', '')
            logger.info(f"📥 LLaMA raw response received ({len(raw_text)} chars)")
            
            # Try to extract JSON
            poll_data = extract_json_from_text(raw_text)
            
            if poll_data:
                # Validate poll data
                if not all(key in poll_data for key in ["title", "question", "options"]):
                    logger.error("Generated poll missing required fields")
                    return None
                    
                if len(poll_data.get("options", [])) != 4:
                    logger.error("Generated poll must have exactly 4 options")
                    return None
                    
                # Log the generated poll for verification
                logger.info("Generated poll:")
                logger.info(f"Title: {poll_data['title']}")
                logger.info(f"Question: {poll_data['question']}")
                logger.info(f"Options: {poll_data['options']}")
                
                return poll_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating poll with Llama: {str(e)}")
            return None
    else:
        logger.error("LLAMA_HOST not configured")
        return None

def extract_key_topics(text: str) -> str:
    """Extract key topics from the transcript for better context"""
    try:
        # Simple keyword extraction with better filtering
        if not text:
            return "the main subject"

        # Convert to lowercase
        text = text.lower()

        # Remove punctuation (simplified)
        text = re.sub(r'[^\\w\\s]', '', text)

        # Common English stop words (a basic list)
        stop_words = set([
            "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours",
            "yourself", "yourselves", "he", "him", "his", "himself", "she", "her", "hers",
            "herself", "it", "its", "itself", "they", "them", "their", "theirs", "themselves",
            "what", "which", "who", "whom", "this", "that", "these", "those", "am", "is", "are",
            "was", "were", "be", "been", "being", "have", "has", "had", "having", "do", "does",
            "did", "doing", "a", "an", "the", "and", "but", "if", "or", "because", "as", "until",
            "while", "of", "at", "by", "for", "with", "about", "against", "between", "into",
            "through", "during", "before", "after", "above", "below", "to", "from", "up", "down",
            "in", "out", "on", "off", "over", "under", "again", "further", "then", "once", "here",
            "there", "when", "where", "why", "how", "all", "any", "both", "each", "few", "more",
            "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so",
            "than", "too", "very", "s", "t", "can", "will", "just", "don", "should", "now", "ll", 
            "m", "o", "re", "ve", "y", "ain", "aren", "couldn", "didn", "doesn", "hadn", "hasn", 
            "haven", "isn", "ma", "mightn", "mustn", "needn", "shan", "shouldn", "wasn", "weren", 
            "won", "wouldn", "okay", "yeah", "yes", "right"
        ])

        words = text.split()
        
        # Filter out stop words and very short words
        filtered_words = [word for word in words if word not in stop_words and len(word) > 2]

        if not filtered_words:
            return "the main subject" # Fallback if no meaningful words left

        # Count word frequencies
        word_counts = {}
        for word in filtered_words:
            word_counts[word] = word_counts.get(word, 0) + 1
        
        # Sort words by frequency in descending order
        sorted_words = sorted(word_counts.items(), key=lambda item: item[1], reverse=True)
        
        # Get the top 2-3 topics
        num_topics = min(len(sorted_words), 3)
        top_topics = [word[0] for word in sorted_words[:num_topics]]
        
        if not top_topics:
             return "the main subject" # Fallback

        return ", ".join(top_topics)

    except Exception as e:
        logger.error(f"Error extracting key topics: {str(e)}")
        return "the main subject" # Fallback in case of any error

def format_poll_for_zoom(poll_data: Dict[str, Any]) -> Dict[str, Any]:
    """Format poll data in the structure expected by Zoom API"""
    return {
        "title": poll_data.get("title", "Meeting Poll"),
        "questions": [
            {
                "name": poll_data.get("question", "What do you think?"),
                "type": "single",
                "answers": poll_data.get("options", ["Yes", "No", "Maybe", "Not sure"])
            }
        ]
    }

def post_poll(poll_data: Dict[str, Any], meeting_id: str) -> Optional[Dict[str, Any]]:
    """Post a poll to the Zoom meeting"""
    if not meeting_id:
        logger.error("Meeting ID not provided")
        return None
    
    if not poll_data:
        logger.error("Poll data not provided")
        return None
    
    # Log the poll details
    title = poll_data.get("title", "No title")
    question = poll_data.get("question", "No question")
    options = poll_data.get("options", [])
    
    logger.info(f"✅ Successfully generated poll:")
    logger.info(f"Title: {title}")
    logger.info(f"Question: {question}")
    logger.info(f"Options: {options}")
    
    # Format for Zoom API
    zoom_poll = format_poll_for_zoom(poll_data)
    
    # Post to Zoom
    token = os.environ.get("ZOOM_TOKEN")
    if not token:
        logger.error("ZOOM_TOKEN environment variable not set")
        return None
    
    logger.info(f"📤 Posting poll to Zoom: {title} - {question}")
    logger.info(f"Options: {options}")
    
    # Use our Zoom API module to post the poll
    response = post_poll_to_meeting(meeting_id, zoom_poll, token)
    
    if response:
        logger.info(f"✅ Poll posted successfully: {response}")
        # Notify the user to launch the poll manually (current Zoom API limitation)
        logger.info("Poll created. Please launch it manually from the Zoom client.")
        return response
    else:
        logger.error("❌ Failed to post poll to Zoom")
        return None

def generate_and_post_poll(transcription: str, meeting_id: str) -> Optional[Dict[str, Any]]:
    """Generate a poll based on transcription and post it to the Zoom meeting"""
    # Generate poll data
    poll_data = generate_poll_with_llama(transcription)
    
    if not poll_data:
        logger.warning("Could not generate poll from transcription")
        return None
    
    # Post the poll to Zoom
    return post_poll(poll_data, meeting_id)

if __name__ == "__main__":
    # Test with sample transcription
    sample_text = """
    So I think for the next quarter, we should focus on improving our customer retention rates.
    The current churn is about 5% monthly, which is too high compared to industry standards.
    We could implement a new loyalty program, improve our customer support response times,
    or even consider a discount for annual subscriptions. What do you all think would work best?
    """
    
    poll = generate_poll_with_llama(sample_text)
    print(json.dumps(poll, indent=2))
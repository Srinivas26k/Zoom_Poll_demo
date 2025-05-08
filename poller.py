#poller.py
import json
import requests
import re
from openai import OpenAI
from rich.console import Console
import config
from poll_prompt import POLL_PROMPT

console = Console()
llama = OpenAI(base_url=config.LLAMA_HOST, api_key="ollama")

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

def generate_poll_from_transcript(transcript: str) -> tuple[str, str, list[str]]:
    """
    Generate a poll from a transcript using LLaMA and the imported prompt.

    Args:
        transcript (str): The meeting transcript to analyze.

    Returns:
        tuple: (title, question, options) of the generated poll.
    """
    # Clean and prepare the transcript
    clean_transcript = transcript.strip()
    if not clean_transcript:
        console.log("[yellow]⚠️ Empty transcript provided[/]")
        return ("Meeting Poll", "What was discussed?", 
                ["Option 1", "Option 2", "Option 3", "Option 4"])
    
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
            console.log(f"[green]✅ Poll posted successfully[/]: {response.json()}")
            return True
        else:
            console.log(f"[red]❌ Zoom API error[/]: {response.status_code} {response.text}")
            return False
    except Exception as e:
        console.log(f"[red]❌ Poll posting error[/]: {e}")
        return False

if __name__ == "__main__":
    # Example usage
    sample_transcript = "Team discussed project timeline. Alice: 'We should extend it.' Bob: 'No, add resources instead.'"
    title, question, options = generate_poll_from_transcript(sample_transcript)
    console.log(f"Generated Poll: {title} - {question} - {options}")
    # Uncomment to test Zoom posting (requires config with meeting_id and token)
    # post_poll_to_zoom(title, question, options, config.MEETING_ID, config.ZOOM_TOKEN)
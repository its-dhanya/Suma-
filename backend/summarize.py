import os
import json
import requests
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
from typing import List, Dict
from langchain.output_parsers import PydanticOutputParser

# === Load environment variables ===
load_dotenv()
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:latest")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

# === System prompt for structured note generation ===
SYSTEM_PROMPT = (
    "You are an expert educational assistant. Your task is to read a transcript of a lecture and generate a high-quality, structured summary that is strictly in valid JSON format, following the schema below. "
    "Your response MUST ONLY contain the JSON object and NOTHING else. Do NOT include any markdown, backticks, additional delimiters, explanations, or commentary. Every character of your output must be valid JSON. "
    "RULES: "
    "Output exactly one valid JSON object that conforms to the schema provided. "
    "Do not include any characters before or after the JSON. No markdown formatting, code fences, or extra text. "
    "If any expected data is missing (such as examples, detailed content, questions, or resources), generate logical and high-quality content based on the lecture topic. "
    "Always include at least 3 revision questions and 2 relevant resources in your output. "
    "Validate your output as valid JSON. If your output is not valid JSON, regenerate it until it is. "
    "Do not output any explanations or commentary; output only the JSON. "
    "FOCUS: "
    "High accuracy, clarity, and academic tone. "
    "Succinct, meaningful phrasing that extracts the core insights from the transcript. "
    "Avoid repetition, generic filler, or any extraneous details. "
    "JSON SCHEMA (output MUST match exactly this structure): "
    "{ "
    '"overview": "2-3 line high-level summary of the lecture.", '
    '"core_concepts": ["concept 1", "concept 2", "..."], '
    '"detailed_explanation": "A paragraph-wise breakdown of the entire lecture content.", '
    '"examples": "Examples or use cases mentioned in the lecture.", '
    '"takeaways": ["key point 1", "key point 2", "..."], '
    '"questions": [ '
    '{ "question": "revision question 1", "answer": "the answer to question 1" }, '
    '{ "question": "revision question 2", "answer": "the answer to question 2" }, '
    '{ "question": "revision question 3", "answer": "the answer to question 3" }'
    '], '
    '"resources": [ '
    '{ "title": "Resource Title (e.g. YouTube Channel, Website, Book)", "type": "Type (e.g. YouTube, Blog, Book)", "url": "Resource URL" }, '
    '{ "title": "Another Resource Title", "type": "Type", "url": "Resource URL" }'
    '] '
    "}"
)

def try_fix_json(raw_text: str) -> str:
    """
    A simple heuristic to fix slight JSON malformation.
    For example, if a closing brace is missing, add it.
    """
    diff = raw_text.count('{') - raw_text.count('}')
    if diff == 1:
        raw_text += "}"
    return raw_text

# === Pydantic models representing the JSON schema ===
class Question(BaseModel):
    question: str
    answer: str

class Resource(BaseModel):
    title: str
    type: str
    url: str

class LectureSummary(BaseModel):
    overview: str
    core_concepts: List[str]
    detailed_explanation: str
    examples: str
    takeaways: List[str]
    questions: List[Question]
    resources: List[Resource]

# Initialize output parser using LangChain's PydanticOutputParser
output_parser = PydanticOutputParser(pydantic_object=LectureSummary)

def summarize(text: str) -> dict:
    print("INFO: Starting structured summarization via Ollama")
    if not text.strip():
        print("WARN: Empty text provided to summarizer")
        return {}

    full_prompt = f"{SYSTEM_PROMPT}\n\nLecture Content:\n{text}"
    combined = ""
    use_stream = True

    try:
        print("INFO: Sending streaming request to Ollama")
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": full_prompt},
            timeout=300,
            stream=True
        )
        response.raise_for_status()
        print(f"INFO: Ollama streaming response status: {response.status_code}")

        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                obj = json.loads(line)
                combined += obj.get("response", "")
            except json.JSONDecodeError:
                combined += line

        combined = combined.strip()
        print("DEBUG: Raw streamed response:")
        print(combined)

    except Exception as e:
        print(f"WARN: Streaming failed ({e}), falling back to non-streaming mode")
        use_stream = False

    if not use_stream:
        try:
            print("INFO: Sending non-streaming request to Ollama")
            resp = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={"model": OLLAMA_MODEL, "prompt": full_prompt, "stream": False},
                timeout=300
            )
            resp.raise_for_status()
            payload = resp.json()
            combined = payload.get("response", "").strip()
            print("DEBUG: Raw non-streamed response:")
            print(combined)
        except Exception as ex:
            print(f"ERROR: Non-streaming fallback failed: {ex}")
            return {"raw": combined or "No response received."}

    try:
        start = combined.find('{')
        end = combined.rfind('}')
        if start == -1 or end == -1 or end <= start:
            raise ValueError("No valid JSON object found in model response")
        json_str = combined[start:end+1]
        try:
            structured_json = json.loads(json_str)
        except Exception:
            print("WARN: Initial parsing failed, attempting to fix JSON")
            fixed_json_str = try_fix_json(json_str)
            structured_json = json.loads(fixed_json_str)
        print("INFO: Successfully parsed structured JSON summary")
        return structured_json
    except Exception as ex:
        print(f"ERROR: Failed to parse JSON from LLM output: {ex}")
        print("DEBUG: Raw combined output:")
        print(combined)
        print("INFO: Returning raw response instead of blank summary")
        return {"raw": combined}

# Example usage:
if __name__ == "__main__":
    lecture_text = "Your lecture transcript goes here..."
    summary_output = summarize(lecture_text)
    print("Final structured summary:")
    print(json.dumps(summary_output, indent=2))
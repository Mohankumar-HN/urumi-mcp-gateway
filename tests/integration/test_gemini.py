
from backend.chat.agent import ask_gemini

if __name__ == "__main__":
    answer = ask_gemini(
        "Reply with exactly: Gemini connection successful"
    )
    print(answer)

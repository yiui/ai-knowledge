from app.core.llm import ask_llm


def chat_with_ai(question: str) -> str:
    return ask_llm(question)
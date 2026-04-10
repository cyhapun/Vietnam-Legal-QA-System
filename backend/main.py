import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
from pathlib import Path

# Đã thay thế Google và OpenAI bằng Hugging Face
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage
from fastapi.middleware.cors import CORSMiddleware

# Cấu hình môi trường
current_dir = Path(__file__).resolve().parent
env_path = current_dir.parent / ".env"

print("Khởi động hệ thống RAG FAISS LCEL")

if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    print("Đã load API key")

from rag_service import init_vector_db, get_retriever, format_docs_for_frontend

try:
    init_vector_db()
    retriever = get_retriever()
except Exception as e:
    print(f"Lỗi khởi tạo vector database {e}")

app = FastAPI(title="VietLaw RAG Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Schema request (đã xóa provider)
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    model: str # Bắt buộc phải có model truyền từ frontend

# Khởi tạo LLM sử dụng Hugging Face Inference
def get_llm(model_name: str):
    hf_token = os.getenv("HUGGINGFACE_API_KEY")
    if not hf_token:
        raise ValueError("Không tìm thấy HUGGINGFACE_API_KEY. Vui lòng cấu hình trong file .env")

    # Tạo endpoint kết nối tới model trên Hugging Face
    llm = HuggingFaceEndpoint(
        repo_id=model_name,
        task="text-generation",
        max_new_tokens=1024,
        temperature=0.1,
        huggingfacehub_api_token=hf_token,
        # Thêm các tham số này để tránh lỗi với một số model chat
        do_sample=True,
        repetition_penalty=1.1,
    )
    
    # Bọc bằng ChatHuggingFace để tương thích với ChatPromptTemplate (roles: system, human, ai)
    return ChatHuggingFace(llm=llm)

prompt = ChatPromptTemplate.from_messages([
    ("system", """
You are a professional Virtual Legal Assistant.

Your PRIMARY task is to answer legal questions strictly based on the provided DOCUMENTS.

====================
STRICT RULES:
1. ONLY use information from the DOCUMENTS section.
2. DO NOT use external knowledge.
3. If the answer is not found in the documents, respond with:
   "Rất tiếc, thông tin bạn hỏi không được đề cập trong tài liệu hiện có."
4. DO NOT provide personalized legal advice or suggest specific actions.
5. Keep answers neutral, factual, and non-speculative.

====================
OUT-OF-SCOPE HANDLING:
If the user asks casual, greeting, or non-legal questions:
- Respond briefly, politely, and naturally.
- Gently introduce yourself as a legal assistant.
- Encourage the user to ask legal-related questions.

====================
RESPONSE LANGUAGE:
- ALWAYS respond in Vietnamese.

====================
RESPONSE FORMAT (ONLY for legal questions):
- **Giải thích chi tiết**:
- **Trích dẫn căn cứ**:

--------------------
DOCUMENTS:
{context}
"""),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{question}")
])

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        last_message = request.messages[-1].content

        chat_history = []
        for msg in request.messages[:-1]:
            if msg.role == "user":
                chat_history.append(HumanMessage(content=msg.content))
            else:
                chat_history.append(AIMessage(content=msg.content))

        retrieved_docs = await retriever.ainvoke(last_message)
        context_text = "\n\n".join(doc.page_content for doc in retrieved_docs)
        frontend_context = format_docs_for_frontend(retrieved_docs)

        inputs = {
            "context": context_text,
            "chat_history": chat_history,
            "question": last_message
        }

        # Gọi LLM với model truyền từ frontend
        llm = get_llm(request.model)
        rag_chain = prompt | llm | StrOutputParser()

        output_text = await rag_chain.ainvoke({
            "context": context_text,
            "chat_history": chat_history,
            "question": last_message
        })

        return {
            "text": output_text,
            "contextUsed": frontend_context
        }

    except Exception as e:
        import traceback
        traceback.print_exc() 
        error_msg = f"Lỗi chi tiết: {type(e).__name__} - {str(e)}"
        print(f"Lỗi backend: {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
from pathlib import Path

# Import các thư viện LLM cần thiết
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI  # Thêm cái này cho OpenAI và OpenRouter

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

# Khởi tạo vector database khi server start
try:
    init_vector_db()
    retriever = get_retriever()
except Exception as e:
    print(f"Lỗi khởi tạo vector database {e}")

# Khởi tạo FastAPI
app = FastAPI(title="VietLaw RAG Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Schema request
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    provider: str = "gemini"
    model: Optional[str] = None

# Khởi tạo LLM linh hoạt theo yêu cầu
def get_llm(provider: str, model_name: str):
    temperature = 0.1 # Mức độ sáng tạo
    
    if provider == "gemini":
        return ChatGoogleGenerativeAI(
            model=model_name or "gemini-2.5-flash-lite", 
            temperature=temperature
        )
        
    elif provider == "openai":
        return ChatOpenAI(
            model=model_name or "gpt-4o-mini", 
            temperature=temperature,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
    elif provider == "openrouter":
        # OpenRouter sử dụng chuẩn API giống OpenAI, chỉ cần đổi base_url
        return ChatOpenAI(
            model=model_name or "anthropic/claude-3.5-sonnet",
            temperature=temperature,
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1"
        )
        
    else:
        # Fallback mặc định nếu provider bị sai
        return ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=temperature)

# Prompt điều khiển AI
prompt = ChatPromptTemplate.from_messages([
    ("system", """
You are a professional Virtual Legal Assistant. Your task is to answer user questions strictly based on the provided documents.

STRICT RULES:
1. ONLY use information from the "DOCUMENTS" section. Do NOT use external knowledge.
2. If the documents do not contain the answer, respond with: "Rất tiếc, thông tin bạn hỏi không được đề cập trong tài liệu hiện có."
3. For casual greetings, respond politely and briefly.
4. Do NOT provide personalized legal advice or encourage any specific actions.
5. You may provide general guidance, but it must be neutral, well-grounded, and non-provocative.

RESPONSE REQUIREMENTS:
- The answer MUST be written in Vietnamese.
- Use formal, neutral, and professional legal language.

RESPONSE STRUCTURE:
- **Giải thích chi tiết**: (Analyze based on the provided documents)
- **Trích dẫn căn cứ**: (Quote the exact Article, Clause, or relevant text from the documents)

---
DOCUMENTS:
{context}
"""),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{question}")
])

# API chat
@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        # Lấy câu hỏi mới nhất
        last_message = request.messages[-1].content

        # Chuyển lịch sử chat sang định dạng LangChain
        chat_history = []
        for msg in request.messages[:-1]:
            if msg.role == "user":
                chat_history.append(HumanMessage(content=msg.content))
            else:
                chat_history.append(AIMessage(content=msg.content))

        # Chuyển invoke -> ainvoke để mượt mà (không chặn server)
        retrieved_docs = await retriever.ainvoke(last_message)

        context_text = "\n\n".join(doc.page_content for doc in retrieved_docs)
        frontend_context = format_docs_for_frontend(retrieved_docs)

        # Chuẩn bị dữ liệu đầu vào cho Prompt
        inputs = {
            "context": context_text,
            "chat_history": chat_history,
            "question": last_message
        }

        # ==========================================
        # ĐOẠN CODE ĐỂ PRINT PROMPT HOÀN THIỆN
        # ==========================================
        formatted_prompt = prompt.format_messages(**inputs)
        
        print("\n" + "="*30 + " FULL PROMPT SENT TO AI " + "="*30)
        for message in formatted_prompt:
            # message.type sẽ là 'system', 'human' hoặc 'ai'
            print(f"[{message.type.upper()}]:")
            print(message.content)
            print("-" * 20)
        print("="*84 + "\n")
        # ==========================================

        # Lắp ráp Chain ngay trong endpoint
        llm = get_llm(request.provider, request.model)
        rag_chain = prompt | llm | StrOutputParser()

        # Gọi LLM
        output_text = await rag_chain.ainvoke({
            "context": context_text,
            "chat_history": chat_history,
            "question": last_message
        })

        # Trả kết quả
        return {
            "text": output_text,
            "contextUsed": frontend_context
        }

    except Exception as e:
        # In đầy đủ chi tiết lỗi ra Console để bạn copy xem dòng nào lỗi
        import traceback
        traceback.print_exc() 
        
        error_msg = f"Lỗi chi tiết: {type(e).__name__} - {str(e)}"
        print(f"Lỗi backend: {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)

# Chạy server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
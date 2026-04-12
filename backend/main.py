import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
from pathlib import Path

from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage
from fastapi.middleware.cors import CORSMiddleware

current_dir = Path(__file__).resolve().parent
env_path = current_dir.parent / ".env"

if env_path.exists():
    load_dotenv(dotenv_path=env_path)

from rag_service import init_vector_db, get_retriever, build_nested_context, format_docs_for_frontend

try:
    init_vector_db()
except Exception as e:
    print(f"Lỗi khởi tạo vector database {e}")

app = FastAPI(title="VietLaw RAG Backend - Nested Schema")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    model: str 
    category: str = "Chung" # Bổ sung Category từ Frontend

def get_llm(model_name: str):
    hf_token = os.getenv("HUGGINGFACE_API_KEY")
    if not hf_token:
        raise ValueError("Không tìm thấy HUGGINGFACE_API_KEY")

    llm = HuggingFaceEndpoint(
        repo_id=model_name,
        task="text-generation",
        max_new_tokens=1500,
        temperature=0.1,
        huggingfacehub_api_token=hf_token,
        do_sample=True,
        repetition_penalty=1.1,
    )
    return ChatHuggingFace(llm=llm)

# Cập nhật chuẩn System Prompt theo kiến trúc Nested Attribution
prompt = ChatPromptTemplate.from_messages([
    ("system", """
BẠN LÀ CHUYÊN GIA PHÁP LUẬT ĐA LĨNH VỰC.
Nhiệm vụ của bạn là giải đáp thắc mắc dựa trên các "Gói dữ liệu căn cứ" được cung cấp.

QUY TẮC PHẢI TUÂN THỦ:
1. TRÍCH DẪN RÕ RÀNG: Luôn bắt đầu câu trả lời bằng việc nêu rõ tên Luật, Chương, Điều, Khoản.
2. XỬ LÝ DẪN CHIẾU: Khi thấy mục "DẪN CHIẾU CHO CĂN CỨ NÀY", hãy sử dụng nội dung đó để giải thích trực tiếp cho các cụm từ tương ứng trong khoản đó.
3. KHÔNG SUY DIỄN: Chỉ trả lời dựa trên nội dung trong các khối dữ liệu. Nếu dữ liệu không đề cập, hãy nói "Hiện tại tài liệu hệ thống cung cấp chưa đủ để giải đáp chi tiết vấn đề này".
4. LUÔN trả lời bằng tiếng Việt chuyên nghiệp, khách quan.

====================
DỮ LIỆU CĂN CỨ PHÁP LÝ HỆ THỐNG TRÍCH XUẤT ĐƯỢC:
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

        # Khởi tạo retriever với filter theo Category
        retriever = get_retriever(category=request.category)
        retrieved_docs = await retriever.ainvoke(last_message)
        
        # Build Context lồng ghép (Nested Context) đã tích hợp Cross-references
        context_text = build_nested_context(retrieved_docs)
        frontend_context = format_docs_for_frontend(retrieved_docs)

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
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
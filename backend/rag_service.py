import os
import json
import glob
import time
from typing import List, Dict, Any
from dotenv import load_dotenv

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain_huggingface import HuggingFaceEndpointEmbeddings

load_dotenv()

FAISS_INDEX_PATH = "./vietlaw_faiss_index"
JSON_DATA_PATH = "./data/processed" 
TRACKING_FILE = "./embedded_files.json" # File theo dõi tiến độ

HF_TOKEN = os.getenv("HUGGINGFACE_API_KEY")
if not HF_TOKEN:
    raise ValueError("Không tìm thấy HUGGINGFACE_API_KEY. Vui lòng cấu hình trong file .env")

print("Đang kết nối mô hình BAAI/bge-m3 qua Hugging Face API...")
embeddings = HuggingFaceEndpointEmbeddings(
    model="BAAI/bge-m3",
    task="feature-extraction",
    huggingfacehub_api_token=HF_TOKEN,
)

vectorstore = None
KNOWLEDGE_BASE = {} 
LAW_METADATA = {}

def determine_category(law_name: str) -> str:
    law_name = law_name.lower()
    if "kinh doanh" in law_name or "doanh nghiệp" in law_name or "thương mại" in law_name: return "Kinh doanh"
    if "đất đai" in law_name: return "Đất đai"
    if "môi trường" in law_name: return "Bảo vệ môi trường"
    if "tố tụng" in law_name: return "Tố tụng dân sự"
    if "nhà ở" in law_name: return "Nhà ở"
    return "Khác"

def load_knowledge_base_to_ram():
    """Nạp toàn bộ dữ liệu JSON vào RAM để Chatbot hoạt động siêu tốc (Không gọi API HF)"""
    global KNOWLEDGE_BASE, LAW_METADATA
    json_files = glob.glob(os.path.join(JSON_DATA_PATH, "*.json"))
    
    print(f"Đang nạp {len(json_files)} file JSON vào RAM (Global Store)...")
    for file_path in json_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            law_info = data.get("law_info", {})
            clauses = data.get("clauses", [])
            
            law_id = law_info.get("law_id")
            law_name = law_info.get("law_name", "")
            
            LAW_METADATA[law_id] = {
                "law_name": law_name,
                "summary": law_info.get("executive_summary", ""),
                "category": determine_category(law_name)
            }
            
            for clause in clauses:
                KNOWLEDGE_BASE[clause["id"]] = {
                    "law_id": law_id,
                    "position": clause.get("position", {}),
                    "content": clause.get("content", ""),
                    "cross_references": clause.get("cross_references", [])
                }
    print("Nạp RAM hoàn tất!")

def get_processed_files() -> List[str]:
    """Đọc danh sách các file đã nhúng xong từ ổ cứng"""
    if os.path.exists(TRACKING_FILE):
        with open(TRACKING_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def mark_file_as_processed(filename: str):
    """Đánh dấu file đã hoàn thành để lần sau bỏ qua"""
    processed = get_processed_files()
    if filename not in processed:
        processed.append(filename)
        with open(TRACKING_FILE, 'w', encoding='utf-8') as f:
            json.dump(processed, f, ensure_ascii=False, indent=4)

def init_vector_db():
    global vectorstore
    
    # 1. Luôn nạp JSON vào RAM trước để Bot có thể truy xuất nội dung
    load_knowledge_base_to_ram()
    
    # 2. Đọc file theo dõi và load FAISS hiện tại (nếu có)
    processed_files = get_processed_files()
    all_json_files = glob.glob(os.path.join(JSON_DATA_PATH, "*.json"))
    pending_files = [f for f in all_json_files if os.path.basename(f) not in processed_files]
    
    if os.path.exists(FAISS_INDEX_PATH):
        print("Đang load FAISS Index từ ổ cứng...")
        vectorstore = FAISS.load_local(
            FAISS_INDEX_PATH,
            embeddings,
            allow_dangerous_deserialization=True
        )
    
    if not pending_files:
        print(">> TẤT CẢ CÁC FILE ĐÃ ĐƯỢC EMBEDDING! Hệ thống sẵn sàng.")
        return

    # 3. Tiến hành Embedding TỪNG FILE MỘT
    print(f"Còn {len(pending_files)} file chưa được nhúng.")
    file_to_process = pending_files[0] # Chỉ lấy file đầu tiên trong danh sách chờ
    filename = os.path.basename(file_to_process)
    
    print(f"==================================================")
    print(f" BẮT ĐẦU EMBEDDING: {filename}")
    print(f"==================================================")
    
    splits = []
    with open(file_to_process, 'r', encoding='utf-8') as f:
        data = json.load(f)
        law_id = data.get("law_info", {}).get("law_id")
        category = determine_category(data.get("law_info", {}).get("law_name", ""))
        
        for clause in data.get("clauses", []):
            metadata = {
                "id": clause["id"],
                "law_id": law_id,
                "category": category,
            }
            doc = Document(page_content=clause.get("content", ""), metadata=metadata)
            splits.append(doc)
            
    print(f"Số lượng chunk cần nhúng của file này: {len(splits)}")
    
    # MICRO-BATCHING: Tránh Timeout bằng cách chia nhỏ gói tin gửi đi
    BATCH_SIZE = 32 # Giảm từ 100 xuống 32 để API dễ thở hơn
    MAX_RETRIES = 3 # Số lần thử lại tối đa cho mỗi batch nếu bị lỗi

    for i in range(0, len(splits), BATCH_SIZE):
        batch = splits[i:i+BATCH_SIZE]
        print(f"  + Đang đẩy lên HuggingFace batch {i} đến {i+len(batch)}...")
        
        success = False
        for attempt in range(MAX_RETRIES):
            try:
                if vectorstore is None:
                    vectorstore = FAISS.from_documents(batch, embeddings, distance_strategy=DistanceStrategy.COSINE)
                else:
                    vectorstore.add_documents(batch)
                    
                # Nghỉ 5 giây giữa các batch bình thường
                time.sleep(5) 
                success = True
                break # Nếu thành công thì thoát vòng lặp retry, đi tới batch tiếp theo
                
            except Exception as e:
                print(f"    -> [Cảnh báo] Lỗi kết nối ở lần thử {attempt + 1}/{MAX_RETRIES}: {str(e)[:100]}...")
                if attempt < MAX_RETRIES - 1:
                    # Thời gian chờ tăng dần: Lần 1 đợi 15s, lần 2 đợi 30s
                    wait_time = 15 * (attempt + 1) 
                    print(f"    -> Đang tạm nghỉ {wait_time} giây để máy chủ phục hồi trước khi thử lại...")
                    time.sleep(wait_time)
                else:
                    print(f"\n[X] THẤT BẠI HOÀN TOÀN TẠI BATCH {i} SAU {MAX_RETRIES} LẦN THỬ.")
                    print("Hãy tắt server và chạy lại sau vài phút. Dữ liệu các batch trước chưa được lưu.")
                    raise e # Văng lỗi để thoát chương trình
            
    # 4. Lưu lại sau khi xong trọn vẹn 1 file
    vectorstore.save_local(FAISS_INDEX_PATH)
    mark_file_as_processed(filename)
    
    print(f">> ĐÃ HOÀN THÀNH VÀ LƯU FILE: {filename}")

    if len(pending_files) - 1 > 0:
        print(f">> Còn {len(pending_files) - 1} file. Bạn có thể restart server để nhúng file tiếp theo.")


def get_retriever(category: str = "Chung"):
    global vectorstore
    if vectorstore is None:
        init_vector_db()

    search_kwargs = {"k": 10, "fetch_k": 20, "lambda_mult": 0.8}
    if category and category != "Chung":
        search_kwargs["filter"] = {"category": category}

    return vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs=search_kwargs
    )

def build_nested_context(retrieved_docs: List[Document]) -> str:
    context_blocks = []
    used_law_ids = set()
    
    for i, doc in enumerate(retrieved_docs):
        clause_id = doc.metadata.get("id")
        clause_data = KNOWLEDGE_BASE.get(clause_id)
        if not clause_data: continue
        
        law_id = clause_data["law_id"]
        used_law_ids.add(law_id)
        
        pos = clause_data["position"]
        law_name = LAW_METADATA[law_id]["law_name"]
        
        block = f"[CĂN CỨ #{i+1}]\n"
        block += f"- Nguồn: {law_name} | Chương {pos.get('chapter')} | Điều {pos.get('article')} | Khoản {pos.get('clause')}\n"
        block += f"- Nội dung: \"{clause_data['content']}\"\n"
        
        refs = clause_data.get("cross_references", [])
        if refs:
            block += "   >> DẪN CHIẾU BỔ SUNG:\n"
            for ref in refs:
                target_id = ref.get("target_id")
                target_data = KNOWLEDGE_BASE.get(target_id)
                if target_data:
                    target_law_name = LAW_METADATA[target_data["law_id"]]["law_name"]
                    target_content = target_data["content"]
                    block += f"   + {ref.get('anchor_text')} ({target_law_name}): \"{target_content}\"\n"
        
        context_blocks.append(block)
    
    header = "--- THÔNG TIN CÁC VĂN BẢN ĐƯỢC SỬ DỤNG ---\n"
    for l_id in used_law_ids:
        meta = LAW_METADATA[l_id]
        header += f"- {meta['law_name']}: {meta['summary']}\n"
    header += "\n--- CHI TIẾT CĂN CỨ VÀ DẪN CHIẾU ---\n"
    
    return header + "\n\n".join(context_blocks)

def format_docs_for_frontend(docs) -> List[Dict[str, Any]]:
    formatted = []
    for doc in docs:
        c_id = doc.metadata.get("id")
        data = KNOWLEDGE_BASE.get(c_id, {})
        if not data: continue
        
        pos = data.get("position", {})
        law_name = LAW_METADATA.get(data.get("law_id"), {}).get("law_name", "")
        
        formatted.append({
            "content": data.get("content", ""),
            "metadata": {
                "source": law_name,
                "dieu": pos.get("article"),
                "khoan": pos.get("clause"),
                "law": law_name
            }
        })
    return formatted
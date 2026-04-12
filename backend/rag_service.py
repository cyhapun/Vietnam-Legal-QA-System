import os
import json
import glob
import time
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain_huggingface import HuggingFaceEndpointEmbeddings

# Tải các biến môi trường (như API keys) từ file .env
load_dotenv()

# --- CẤU HÌNH ĐƯỜNG DẪN ---
FAISS_INDEX_PATH = "./vietlaw_faiss_index"
JSON_DATA_PATH = "./data/processed" 
TRACKING_FILE = "./embedded_files.json"

# --- KIỂM TRA & KHỞI TẠO MODEL ---
HF_TOKEN = os.getenv("HUGGINGFACE_API_KEY")
if not HF_TOKEN:
    raise ValueError("Không tìm thấy HUGGINGFACE_API_KEY. Vui lòng kiểm tra lại file .env của bạn nhé.")

print("Đang kết nối mô hình BAAI/bge-m3 qua Hugging Face API...")
embeddings = HuggingFaceEndpointEmbeddings(
    model="BAAI/bge-m3",
    task="feature-extraction",
    huggingfacehub_api_token=HF_TOKEN,
)

# --- BIẾN TOÀN CỤC ---
vectorstore: Optional[FAISS] = None
KNOWLEDGE_BASE: Dict[str, Any] = {} 
LAW_METADATA: Dict[str, Any] = {}

def determine_category(law_name: str) -> str:
    """Phân loại văn bản pháp luật dựa trên tên gọi để dễ dàng lọc (filter) sau này."""
    name_lower = law_name.lower()
    
    # Gom nhóm các từ khóa liên quan để code gọn hơn
    if any(kw in name_lower for kw in ["kinh doanh", "doanh nghiệp", "thương mại"]):
        return "Kinh doanh"
    if "đất đai" in name_lower:
        return "Đất đai"
    if "môi trường" in name_lower:
        return "Bảo vệ môi trường"
    if "tố tụng" in name_lower:
        return "Tố tụng dân sự"
    if "nhà ở" in name_lower:
        return "Nhà ở"
        
    return "Khác"

def load_knowledge_base_to_ram() -> None:
    """Nạp toàn bộ dữ liệu JSON vào RAM để Chatbot truy xuất siêu tốc mà không cần gọi API."""
    global KNOWLEDGE_BASE, LAW_METADATA
    json_files = glob.glob(os.path.join(JSON_DATA_PATH, "*.json"))
    
    print(f"Đang nạp {len(json_files)} file JSON vào bộ nhớ...")
    
    for file_path in json_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            law_info = data.get("law_info", {})
            clauses = data.get("clauses", [])
            
            law_id = law_info.get("law_id")
            law_name = law_info.get("law_name", "")
            
            # Lưu trữ thông tin chung của văn bản luật
            LAW_METADATA[law_id] = {
                "law_name": law_name,
                "summary": law_info.get("executive_summary", ""),
                "category": determine_category(law_name)
            }
            
            # Lưu trữ chi tiết từng điều khoản
            for clause in clauses:
                KNOWLEDGE_BASE[clause["id"]] = {
                    "law_id": law_id,
                    "position": clause.get("position", {}),
                    "content": clause.get("content", ""),
                    "cross_references": clause.get("cross_references", [])
                }
                
    print("Nạp dữ liệu vào RAM hoàn tất!")

def get_processed_files() -> List[str]:
    """Đọc danh sách các file đã được embedding thành công trước đó."""
    if os.path.exists(TRACKING_FILE):
        with open(TRACKING_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def mark_file_as_processed(filename: str) -> None:
    """Đánh dấu file đã xử lý xong để những lần chạy sau hệ thống sẽ bỏ qua."""
    processed = get_processed_files()
    if filename not in processed:
        processed.append(filename)
        with open(TRACKING_FILE, 'w', encoding='utf-8') as f:
            json.dump(processed, f, ensure_ascii=False, indent=4)

def init_vector_db() -> None:
    """Hàm khởi tạo và cập nhật cơ sở dữ liệu vector (FAISS)."""
    global vectorstore
    
    # 1. Nạp dữ liệu vào RAM trước để sẵn sàng phục vụ
    load_knowledge_base_to_ram()
    
    # 2. Tìm các file JSON chưa được xử lý
    processed_files = get_processed_files()
    all_json_files = glob.glob(os.path.join(JSON_DATA_PATH, "*.json"))
    pending_files = [f for f in all_json_files if os.path.basename(f) not in processed_files]
    
    # Tải index cũ nếu đã có
    if os.path.exists(FAISS_INDEX_PATH):
        print("Đang tải FAISS Index từ ổ cứng...")
        vectorstore = FAISS.load_local(
            FAISS_INDEX_PATH,
            embeddings,
            allow_dangerous_deserialization=True
        )
    
    if not pending_files:
        print(">> TẤT CẢ CÁC FILE ĐÃ ĐƯỢC EMBEDDING! Hệ thống sẵn sàng.")
        return

    # 3. Tiến hành nhúng (embedding) TỪNG FILE MỘT để tránh quá tải
    print(f"Còn {len(pending_files)} file chưa được nhúng.")
    file_to_process = pending_files[0] 
    filename = os.path.basename(file_to_process)
    
    print("=" * 50)
    print(f" BẮT ĐẦU EMBEDDING: {filename}")
    print("=" * 50)
    
    splits = []
    with open(file_to_process, 'r', encoding='utf-8') as f:
        data = json.load(f)
        law_id = data.get("law_info", {}).get("law_id")
        category = determine_category(data.get("law_info", {}).get("law_name", ""))
        
        # Đóng gói từng điều khoản thành Document
        for clause in data.get("clauses", []):
            metadata = {
                "id": clause["id"],
                "law_id": law_id,
                "category": category,
            }
            doc = Document(page_content=clause.get("content", ""), metadata=metadata)
            splits.append(doc)
            
    print(f"Số lượng chunk cần nhúng của file này: {len(splits)}")
    
    BATCH_SIZE = 32 
    MAX_RETRIES = 3 

    for i in range(0, len(splits), BATCH_SIZE):
        batch = splits[i:i+BATCH_SIZE]
        print(f"  + Đang đẩy lên HuggingFace batch {i} đến {i+len(batch)}...")
        
        for attempt in range(MAX_RETRIES):
            try:
                # Nếu vectorstore chưa có, tạo mới. Nếu có rồi thì thêm vào.
                if vectorstore is None:
                    vectorstore = FAISS.from_documents(batch, embeddings, distance_strategy=DistanceStrategy.COSINE)
                else:
                    vectorstore.add_documents(batch)
                    
                time.sleep(5) # Nghỉ ngơi một chút giữa các batch để giữ kết nối ổn định
                break         # Thành công thì thoát vòng lặp retry
                
            except Exception as e:
                print(f"    -> [Cảnh báo] Lỗi kết nối ở lần thử {attempt + 1}/{MAX_RETRIES}: {str(e)[:100]}...")
                if attempt < MAX_RETRIES - 1:
                    wait_time = 15 * (attempt + 1) # Chờ lâu hơn sau mỗi lần lỗi (15s -> 30s)
                    print(f"    -> Đang tạm nghỉ {wait_time} giây để máy chủ phục hồi...")
                    time.sleep(wait_time)
                else:
                    print(f"\n[X] THẤT BẠI TẠI BATCH {i} SAU {MAX_RETRIES} LẦN THỬ.")
                    print("Hãy tắt server và chạy lại sau vài phút. Các batch trước của file này chưa được lưu.")
                    raise e
            
    vectorstore.save_local(FAISS_INDEX_PATH)
    mark_file_as_processed(filename)
    
    print(f">> ĐÃ HOÀN THÀNH VÀ LƯU FILE: {filename}")

    if len(pending_files) > 1:
        print(f">> Còn {len(pending_files) - 1} file. Bạn có thể restart server để nhúng file tiếp theo.")


def get_retriever(category: str = "Chung") -> Any:
    """Tạo retriever để tìm kiếm các đoạn văn bản pháp luật liên quan."""
    global vectorstore
    if vectorstore is None:
        init_vector_db()

    search_kwargs = {"k": 10, "fetch_k": 20, "lambda_mult": 0.8}
    
    # Lọc theo chuyên ngành luật nếu có yêu cầu
    if category and category != "Chung":
        search_kwargs["filter"] = {"category": category}

    return vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs=search_kwargs
    )

def build_nested_context(retrieved_docs: List[Document]) -> str:
    """Xây dựng chuỗi ngữ cảnh (context) từ các tài liệu truy xuất được, bao gồm cả dẫn chiếu."""
    context_blocks = []
    used_law_ids = set()
    
    for i, doc in enumerate(retrieved_docs):
        clause_id = doc.metadata.get("id")
        clause_data = KNOWLEDGE_BASE.get(clause_id)
        if not clause_data: 
            continue
        
        law_id = clause_data["law_id"]
        used_law_ids.add(law_id)
        
        pos = clause_data["position"]
        law_name = LAW_METADATA[law_id]["law_name"]
        
        # Tạo khối thông tin cho từng căn cứ
        block = f"[CĂN CỨ #{i+1}]\n"
        block += f"- Nguồn: {law_name} | Chương {pos.get('chapter')} | Điều {pos.get('article')} | Khoản {pos.get('clause')}\n"
        block += f"- Nội dung: \"{clause_data['content']}\"\n"
        
        # Xử lý các điều khoản dẫn chiếu bổ sung
        refs = clause_data.get("cross_references", [])
        if refs:
            block += "   >> DẪN CHIẾU BỔ SUNG:\n"
            for ref in refs:
                target_data = KNOWLEDGE_BASE.get(ref.get("target_id"))
                if target_data:
                    target_law_name = LAW_METADATA[target_data["law_id"]]["law_name"]
                    block += f"   + {ref.get('anchor_text')} ({target_law_name}): \"{target_data['content']}\"\n"
        
        context_blocks.append(block)
    
    # Tạo phần Header tổng hợp thông tin văn bản
    header = "--- THÔNG TIN CÁC VĂN BẢN ĐƯỢC SỬ DỤNG ---\n"
    for l_id in used_law_ids:
        meta = LAW_METADATA[l_id]
        header += f"- {meta['law_name']}: {meta['summary']}\n"
    header += "\n--- CHI TIẾT CĂN CỨ VÀ DẪN CHIẾU ---\n"
    
    return header + "\n\n".join(context_blocks)

def format_docs_for_frontend(docs: List[Document]) -> List[Dict[str, Any]]:
    """Định dạng lại dữ liệu trả về để Frontend dễ dàng hiển thị lên UI."""
    formatted = []
    for doc in docs:
        c_id = doc.metadata.get("id")
        data = KNOWLEDGE_BASE.get(c_id, {})
        if not data: 
            continue
        
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
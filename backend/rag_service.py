import os
import re
import torch
from typing import List, Dict, Any
from dotenv import load_dotenv

from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.vectorstores.utils import DistanceStrategy
# Thay đổi import
from langchain_huggingface import HuggingFaceEndpointEmbeddings

# Load biến môi trường từ file .env
load_dotenv()

# Cấu hình đường dẫn lưu FAISS và thư mục chứa dữ liệu PDF
FAISS_INDEX_PATH = "./vietlaw_faiss_index"
PDF_DATA_PATH = "./data"

# Kích thước chunk phù hợp với văn bản pháp luật
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200

HF_TOKEN = os.getenv("HUGGINGFACE_API_KEY")
if not HF_TOKEN:
    raise ValueError("Không tìm thấy HUGGINGFACE_API_KEY. Vui lòng cấu hình trong file .env")

# Khởi tạo mô hình embedding qua Hugging Face Inference API
print("Đang kết nối mô hình BAAI bge m3 qua Hugging Face API...")
embeddings = HuggingFaceEndpointEmbeddings(
    # model="cyhapun/vn-legal-embedding-v1",
    model="BAAI/bge-m3",
    task="feature-extraction",
    huggingfacehub_api_token=HF_TOKEN,
)
vectorstore = None

# Hàm trích xuất metadata từ nội dung văn bản
# Nhận diện Điều Khoản Điểm theo format luật Việt Nam
def extract_metadata(text: str):
    # Tìm Điều (Ví dụ: Điều 12, Điều 12a)
    dieu = re.search(r'(?i)Điều\s+(\d+[a-z]?)', text)
    
    # Tìm Khoản (Ví dụ: 1., 2.) ở đầu dòng
    khoan = re.search(r'^\s*(\d+)\.', text, re.MULTILINE)
    
    # Tìm Điểm (Ví dụ: a), b), đ)) ở đầu dòng
    diem = re.search(r'^\s*([a-zđ])\)', text, re.MULTILINE | re.IGNORECASE)

    return {
        "dieu": dieu.group(1) if dieu else None,
        "khoan": khoan.group(1) if khoan else None,
        "diem": diem.group(1) if diem else None
    }
# Hàm chia văn bản theo cấu trúc pháp luật
# Thứ tự ưu tiên Điều sau đó Khoản sau đó Điểm
def split_legal_text(doc: Document) -> List[Document]:
    text = "\n" + doc.page_content.strip()
    results = []

    # Tách theo Điều
    dieu_chunks = re.split(r'\n(Điều\s+\d+[a-zA-Z]*[^:\n]*:?)', text, flags=re.IGNORECASE)

    # Phần mở đầu trước Điều đầu tiên
    preamble = dieu_chunks[0].strip()
    if preamble:
        results.append(Document(
            page_content=preamble,
            metadata={**doc.metadata, "dieu": None, "khoan": None, "diem": None}
        ))

    if len(dieu_chunks) == 1:
        return results

    # Xử lý từng Điều
    for i in range(1, len(dieu_chunks), 2):
        dieu_title = dieu_chunks[i].strip()
        dieu_content = dieu_chunks[i + 1].strip() if i + 1 < len(dieu_chunks) else ""

        full_dieu = f"{dieu_title}\n{dieu_content}".strip()

        # Nếu Điều ngắn thì giữ nguyên
        if len(full_dieu) <= CHUNK_SIZE:
            results.append(Document(
                page_content=full_dieu,
                metadata={**doc.metadata, **extract_metadata(full_dieu)}
            ))
            continue

        # Nếu Điều dài thì tách theo Khoản
        khoan_chunks = re.split(r'\n(\d+\.\s)', "\n" + full_dieu)

        dieu_preamble = khoan_chunks[0].strip()
        if dieu_preamble and dieu_preamble != dieu_title:
            results.append(Document(
                page_content=dieu_preamble,
                metadata={**doc.metadata, **extract_metadata(dieu_title)}
            ))

        for j in range(1, len(khoan_chunks), 2):
            khoan_title = khoan_chunks[j].strip()
            khoan_content = khoan_chunks[j + 1].strip() if j + 1 < len(khoan_chunks) else ""

            # Ghép lại Điều và Khoản để giữ ngữ cảnh
            full_khoan = f"{dieu_title}\nKhoản {khoan_title} {khoan_content}".strip()

            if len(full_khoan) <= CHUNK_SIZE:
                results.append(Document(
                    page_content=full_khoan,
                    metadata={**doc.metadata, **extract_metadata(full_khoan)}
                ))
                continue

            # Nếu Khoản vẫn dài thì tách theo Điểm
            diem_chunks = re.split(r'\n([a-zđ]\)\s)', "\n" + full_khoan)

            khoan_preamble = diem_chunks[0].strip()
            if khoan_preamble and khoan_preamble != f"{dieu_title}\nKhoản {khoan_title}":
                results.append(Document(
                    page_content=khoan_preamble,
                    metadata={**doc.metadata, **extract_metadata(khoan_preamble)}
                ))

            for k in range(1, len(diem_chunks), 2):
                diem_title = diem_chunks[k].strip()
                diem_content = diem_chunks[k + 1].strip() if k + 1 < len(diem_chunks) else ""

                # Ghép đầy đủ Điều Khoản Điểm
                full_diem = f"{dieu_title}\nKhoản {khoan_title}\nĐiểm {diem_title} {diem_content}".strip()

                results.append(Document(
                    page_content=full_diem,
                    metadata={**doc.metadata, **extract_metadata(full_diem)}
                ))

    return results

# Fallback splitter dùng khi chunk vẫn quá dài
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=[
        "\n\n",
        "\n",
        ". ",
        " ",
        ""
    ]
)

# Kết hợp legal splitting và recursive splitting
def hybrid_chunking(docs: List[Document]) -> List[Document]:
    splits = []

    for doc in docs:
        legal_chunks = split_legal_text(doc)

        for chunk in legal_chunks:
            if len(chunk.page_content) > CHUNK_SIZE:
                sub_chunks = text_splitter.split_documents([chunk])
                splits.extend(sub_chunks)
            else:
                splits.append(chunk)

    return splits

# Khởi tạo vector database FAISS
def init_vector_db():
    global vectorstore

    if os.path.exists(FAISS_INDEX_PATH):
        print("Đang load FAISS")
        vectorstore = FAISS.load_local(
            FAISS_INDEX_PATH,
            embeddings,
            allow_dangerous_deserialization=True
        )
        print("Load FAISS thành công")
        return

    print("Đang đọc PDF và tiến hành chunking")

    loader = PyPDFDirectoryLoader(PDF_DATA_PATH)
    docs = loader.load()

    if not docs:
        raise ValueError("Không có file PDF")

    print(f"Số lượng tài liệu đã load {len(docs)}")

    splits = hybrid_chunking(docs)

    print(f"Tổng số chunk {len(splits)}")

    print("Đang tạo embedding và FAISS")

    vectorstore = FAISS.from_documents(
        documents=splits,
        embedding=embeddings,
        distance_strategy=DistanceStrategy.COSINE
    )

    vectorstore.save_local(FAISS_INDEX_PATH)
    print("Đã lưu FAISS thành công")

# Tạo retriever dùng cho RAG
def get_retriever():
    global vectorstore
    if vectorstore is None:
        init_vector_db()

    return vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": 8,
            "fetch_k": 30,
            "lambda_mult": 0.8
        }
    )

# Format dữ liệu trả về cho frontend
def format_docs_for_frontend(docs) -> List[Dict[str, Any]]:
    formatted = []

    for doc in docs:
        source_file = doc.metadata.get("source", "").split(os.sep)[-1]

        dieu = doc.metadata.get("dieu")
        khoan = doc.metadata.get("khoan")
        diem = doc.metadata.get("diem")

        formatted.append({
            "content": doc.page_content,
            "metadata": {
                "source": source_file,
                "dieu": dieu,
                "khoan": khoan,
                "diem": diem,
                "law": "Văn bản pháp luật"
            }
        })

    return formatted
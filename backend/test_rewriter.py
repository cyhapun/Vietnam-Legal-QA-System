import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.rewriting.llm_rewriter import LLMRewriter

def main():
    print("Initializing LLMRewriter...")
    rewriter = LLMRewriter()
    
    test_queries = [
        "Xin chào, bạn có khỏe không?",
        "Làm sổ đỏ hết bao nhiêu tiền?",
        "Nhà nước thu hồi đất thì đền bù thế nào?",
        "Tội giết người đi tù bao nhiêu năm?",
    ]
    
    for query in test_queries:
        print(f"\n--- Original Query: {query}")
        domain, queries = rewriter.rewrite(query)
        print(f"Domain: {domain}")
        print("Queries:")
        for q in queries:
            print(f"  - {q}")

if __name__ == "__main__":
    main()

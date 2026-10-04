from vector_store import VectorSearch

class SearchEngine:
    def __init__(self):
        self.vector_store = VectorSearch()

    def index_search_results(self, results: list[dict]):
        docs = []
        ids = []
        for i, res in enumerate(results):
            snippet = res.get("snippet", "")
            title = res.get("title", "")
            url = res.get("url", "")
            
            if snippet:
                doc_text = f"Title: {title}\nURL: {url}\nContent: {snippet}"
                docs.append(doc_text)
                ids.append(f"web_res_{i}_{hash(url)}")
                
        if docs:
            try:
                self.vector_store.add_documents(docs=docs, ids=ids)
            except Exception as e:
                print(f"Vector indexing error: {e}")

    def get_semantic_context(self, query: str, n_results: int = 3) -> str:
        matches = self.vector_store.search(query, n_results=n_results)
        if not matches:
            return "No local vector context available."
            
        context_block = "\n\n---\n\n".join([m["document"] for m in matches])
        return context_block
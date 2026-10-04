from sentence_transformers import SentenceTransformer
import chromadb

class VectorSearch:
    def __init__(self, collection_name: str = "pyseek_docs"):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.client = chromadb.Client()
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def add_documents(self, docs: list[str], ids: list[str]):
        if not docs:
            return
        embeddings = self.model.encode(docs).tolist()
        self.collection.add(
            documents=docs,
            embeddings=embeddings,
            ids=ids
        )

    def search(self, query: str, n_results: int = 3):
        if self.collection.count() == 0:
            return []
        
        query_embedding = self.model.encode([query]).tolist()
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=n_results
        )
        
        matches = []
        if results and 'documents' in results and results['documents']:
            docs = results['documents'][0]
            metas = results['metadatas'][0] if results.get('metadatas') else [{} for _ in docs]
            for doc, meta in zip(docs, metas):
                matches.append({"document": doc, "metadata": meta})
                
        return matches
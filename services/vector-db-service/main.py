from flask import Flask, request, jsonify
import numpy as np
import json
import os
from datetime import datetime

app = Flask(__name__)

# In-memory storage for demo purposes
# In production, use a proper vector database like FAISS, Annoy, or ChromaDB
class SimpleVectorDB:
    def __init__(self):
        self.vectors = {}
        self.metadata = {}

    def add_vector(self, vector_id, vector, metadata=None):
        self.vectors[vector_id] = np.array(vector)
        self.metadata[vector_id] = metadata or {}

    def search(self, query_vector, top_k=5):
        if not self.vectors:
            return []

        query = np.array(query_vector)
        similarities = {}

        for vector_id, vector in self.vectors.items():
            # Cosine similarity
            similarity = np.dot(query, vector) / (np.linalg.norm(query) * np.linalg.norm(vector))
            similarities[vector_id] = similarity

        # Sort by similarity (descending)
        sorted_results = sorted(similarities.items(), key=lambda x: x[1], reverse=True)
        return sorted_results[:top_k]

# Global vector database instance
vector_db = SimpleVectorDB()

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()})

@app.route('/vectors', methods=['POST'])
def add_vector():
    """Add a vector to the database"""
    try:
        data = request.get_json()
        vector_id = data['id']
        vector = data['vector']
        metadata = data.get('metadata', {})

        vector_db.add_vector(vector_id, vector, metadata)

        return jsonify({
            "message": f"Vector {vector_id} added successfully",
            "id": vector_id
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/vectors/search', methods=['POST'])
def search_vectors():
    """Search for similar vectors"""
    try:
        data = request.get_json()
        query_vector = data['vector']
        top_k = data.get('top_k', 5)

        results = vector_db.search(query_vector, top_k)

        response = []
        for vector_id, similarity in results:
            response.append({
                "id": vector_id,
                "similarity": float(similarity),
                "metadata": vector_db.metadata.get(vector_id, {})
            })

        return jsonify({
            "results": response,
            "query_timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/vectors/<vector_id>', methods=['GET'])
def get_vector(vector_id):
    """Get vector metadata"""
    if vector_id not in vector_db.metadata:
        return jsonify({"error": "Vector not found"}), 404

    return jsonify({
        "id": vector_id,
        "metadata": vector_db.metadata[vector_id]
    })

@app.route('/vectors/<vector_id>', methods=['DELETE'])
def delete_vector(vector_id):
    """Delete a vector"""
    if vector_id not in vector_db.vectors:
        return jsonify({"error": "Vector not found"}), 404

    del vector_db.vectors[vector_id]
    del vector_db.metadata[vector_id]

    return jsonify({"message": f"Vector {vector_id} deleted successfully"})

@app.route('/vectors', methods=['GET'])
def list_vectors():
    """List all vectors (metadata only)"""
    return jsonify({
        "vectors": list(vector_db.metadata.keys()),
        "count": len(vector_db.metadata)
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8003))
    app.run(host='0.0.0.0', port=port, debug=True)
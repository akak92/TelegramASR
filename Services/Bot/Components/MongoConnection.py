"""
MongoConnection.py

Gestiona la conexión con MongoDB y las operaciones sobre la colección
de transcripciones médicas.
"""

from pymongo import MongoClient
from bson import ObjectId


class MongoConnection:
    def __init__(self, uri: str, db_name: str, collection_name: str):
        self.client: MongoClient = MongoClient(uri)
        self.collection = self.client[db_name][collection_name]

    def insert_record(self, record: dict) -> str:
        """Inserta un nuevo registro y retorna su ID como string."""
        result = self.collection.insert_one(record)
        return str(result.inserted_id)

    def update_record(self, record_id: str, fields: dict) -> None:
        """Actualiza campos de un registro existente por su ID."""
        self.collection.update_one(
            {"_id": ObjectId(record_id)},
            {"$set": fields},
        )

    def ping(self) -> bool:
        """Verifica la conexión con MongoDB."""
        try:
            self.client.admin.command("ping")
            return True
        except Exception:
            return False

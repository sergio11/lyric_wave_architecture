from elasticsearch import Elasticsearch
from airflow.utils.decorators import apply_defaults
from operators.base_custom_operator import BaseCustomOperator
from bson import ObjectId
from datetime import datetime

class IndexToElasticsearchOperator(BaseCustomOperator):

    @apply_defaults
    def __init__(
        self, 
        elasticsearch_host,
        elasticsearch_index,
        *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.elasticsearch_host = elasticsearch_host
        self.elasticsearch_index = elasticsearch_index

    def execute(self, context):
        self._log_to_mongodb(f"Starting execution of IndexToElasticsearchOperator", context, "INFO")

        # Get the configuration passed to the DAG from the execution context
        dag_run_conf = context['dag_run'].conf

        # Get the song_info_id from the configuration
        song_id = dag_run_conf['song_id']

        # Retrieve song text from MongoDB based on song_id
        collection = self._get_mongodb_collection()
        song_info = collection.find_one({"_id": ObjectId(song_id)})
        song_text = song_info.get('song_text')

        # Index the song text in Elasticsearch
        self._index_song_text_to_elasticsearch(song_id, song_text)

        # Update the document in MongoDB
        collection.update_one({"_id": ObjectId(song_id)}, {
            "$set": {
                "song_status": "song_indexed",
                "song_indexed_at": datetime.now()
            }
        })
        self._log_to_mongodb(f"Updated MongoDB document with ID: {song_id}", context, "INFO")
        self._log_to_mongodb(f"Indexing completed for song ID: {song_id}", context, "INFO")

    def _index_song_text_to_elasticsearch(self, song_id, song_text):
        es = Elasticsearch(self.elasticsearch_host)
        document = {
            'song_id': song_id,
            'song_text': song_text
        }
        es.index(index=self.elasticsearch_index, doc_type='_doc', body=document)
from datetime import datetime
import uuid
from openai import OpenAI
import config
from scylladb import ScyllaClient
import numpy as np
from usearch.index import Index
from sentence_transformers import SentenceTransformer
import ast
import argparse

import warnings
warnings.filterwarnings("ignore", category=UserWarning)

parser = argparse.ArgumentParser()
parser.add_argument('--question', type=str, help='Ask something')
args = parser.parse_args()

question = args.question if args.question else "What is ScyllaDB? Answer in 5 words"

OPENROUTER_API = config.OPENROUTER_API
client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=OPENROUTER_API,
)

scylla_client = ScyllaClient()
session = scylla_client.get_session()

def ask_openai(prompt):
    completion = client.chat.completions.create(
    model="openai/gpt-4.1-nano",
    messages=[{
        "role": "user",
        "content": prompt
        }],
    
    )
    return completion.choices[0].message.content


def insert_data(values:tuple):
    columns = config.SCYLLA_COLUMNS
    cql = f"""INSERT INTO semantic.prompts ({','.join(columns)}) 
              VALUES ({','.join(['%s' for c in columns])});
           """
    session.execute(cql, values)

index = Index(ndim=384)


vector_id_uuid_map = {}

rows = session.execute("SELECT id, prompt_vector FROM semantic.prompts;")
for row in rows:
    if row["prompt_vector"]:
        vector = ast.literal_eval(row["prompt_vector"]) # Convert string representation of list to actual list
        vector = np.array(vector, dtype=np.float32)
        u = row["id"]
        vector_id = int.from_bytes(u.bytes[:8], byteorder="big", signed=False)
        vector_id_uuid_map[vector_id] = u
        index.add(vector_id, vector)


def embed(text):
    model = SentenceTransformer('all-MiniLM-L6-v2')
    return model.encode(text)

def query_index(embedding, k=1, threshold=0.1):
    """Query Usearch for similar prompts"""
    matches = index.search(np.array(embedding, dtype=np.float32), k)
    results = []
    for match in matches:
        if match.distance < threshold:
            results.append((vector_id_uuid_map[match.key], match.distance))
    return results

def cache_result(prompt, response, embedding):
    """Store prompt, response, and embedding"""
    id_ = uuid.uuid4()
    now = datetime.now()
    values = (id_, prompt, response, now, now, str(embedding.tolist()))
    insert_data(values)
    return id_

def semantic_cached_prompt(prompt):
    embedded = embed(prompt)
    matches = query_index(embedded, k=1)
    if len(matches) > 0:
        id_, _ = matches[0]
        cached = session.execute("SELECT response FROM semantic.prompts WHERE id=%s", (id_,)).one()
        print("-----\nCache hit... ScyllaDB query executed succesfully!")
        return cached["response"]
    else:
        response = ask_openai(prompt)
        print("Cache miss... sending request to OpenAI!")
        cache_result(prompt, response, embedded)
        return response


if __name__ == "__main__":
    print("Question:", question)
    answer = semantic_cached_prompt(question)
    print("\nAnswer:", answer)
    
    """ prompt = "What is ScyllaDB? Answer in 5 words"
    response = ask_openai(prompt)
    embedding = embed(prompt)
    cache_result(prompt, response, embedding)"""
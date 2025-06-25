# Semantic caching with ScyllaDB
This is a sample application that shows you how to use ScyllaDB with LLM APIs for semantic caching and avoid unnecesary LLM API requests to save costs.

Start up a new ScyllaDB cluster:
```bash
docker run --name semantic -p "9042:9042" -d scylladb/scylla \
  --overprovisioned 1 \
  --smp 1
```

Connect to ScyllaDB using CQLSH:
```bash
docker exec -it semantic cqlsh
```

Create schema:
```sql
CREATE KEYSPACE semantic
WITH REPLICATION = {
  'class' : 'NetworkTopologyStrategy',
  'replication_factor' : 1
};

CREATE TABLE semantic.prompts (
    id uuid PRIMARY KEY,
    inserted_at timestamp,
    prompt text,
    prompt_vector text,
    response text,
    updated_at timestamp
)
```

## Run the app
Run the program using the `--question` cmd argument:
```
python main.py --question "What's the capital of Hungary?"

python main.py --question "What's the biggest city in Florida?"

python main.py --question "What's the largest city in Florida?"
```

Notice how the program uses cache or not depending on the question.

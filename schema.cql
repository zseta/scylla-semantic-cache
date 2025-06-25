CREATE TABLE semantic.prompts (
    id uuid PRIMARY KEY,
    inserted_at timestamp,
    prompt text,
    prompt_vector text,
    response text,
    updated_at timestamp
)
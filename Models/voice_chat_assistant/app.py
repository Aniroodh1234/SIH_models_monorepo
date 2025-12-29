## importing necessary tokens and environement keys
import os
from dotenv import load_dotenv
load_dotenv()
import json

## importing necessay modules and library to build gen AI application
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser   
from langchain_groq import ChatGroq
from langchain_community.embeddings import HuggingFaceEmbeddings
import chromadb
from chromadb import PersistentClient
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import warnings
warnings.filterwarnings('ignore')


## Groq api key and setting hugging face environment
Groq_api_key = os.getenv('GROQ_API_KEY')
client = os.getenv("HUGGINGFACEHUB_API_TOKEN")

## Langsmith tracking
os.environ["LANGCHAIN_API_KEY"]= os.getenv("LANGCHAIN_API_KEY")
os.environ["LANGCHAIN_TRACING_V2"]= "true"
os.environ["LANGCHAIN_PROJECT"]= "Swaraj Desk interactive multi-lingual RAG chatbot"

## Importing the JSON data
with open("SwarajDesk_vectorDB.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# print(len(data)) #original JSON length


## Vector embeddings using Hugging face sentence transformer
embeddings_list = []   # to store all embeddings + metadata

embedding_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)


for record in data:
    content = record["content"]
    embedding = embedding_model.embed_query(content)
    
    embeddings_list.append({
        "embedding": embedding,
        "title": record["title"],
        "content": record["content"],
        "tags": record["tags"]
    })

# print(len(embeddings_list))  # should match original JSON length 


## storing embedding vectors in chromaDB

# initialize chroma client
client = PersistentClient(path="./chroma_store")


# create / load collection
collection = client.get_or_create_collection(
    name="swarajdesk_chroma_db",       # changed for better naming
    metadata={"hnsw:space": "cosine"}   # similarity metric
)

# store embeddings + metadata in chroma
for idx, item in enumerate(embeddings_list):
    collection.add(
    ids=[str(idx)],
    embeddings=[item["embedding"]],
    documents=[item["content"]],
    metadatas=[
        {
            "title": item["title"],
            "content": item["content"],
            "tags": ", ".join(item["tags"])    # FIX: convert list → string
        }
    ]
)

print("Embeddings stored successfully in ChromaDB!")
# number of stored records.
print(collection.count())                     



## Function to retrieve context from ChromaDB based on user query

def retrieve_context(user_query: str, collection, k: int = 5):
    # 1) Embed the user query using HuggingFace embeddings model
    query_embedding = embedding_model.embed_query(user_query)

    # 2) Query ChromaDB for similarity
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=k
    )

    metadatas = results["metadatas"][0]
    documents = results.get("documents", [[]])[0]

    return metadatas, documents


## checking the user query and embedding vector from chromaDB

# test_query = "How can I reset my password?"
# metadatas, docs = retrieve_context(test_query, collection, k=5)

# print("\nRetrieved Chunks for Query:", test_query)
# for idx, m in enumerate(metadatas):
#     print(f"\nResult #{idx + 1}")
#     print("Title:", m["title"])
#     print("Tags:", m["tags"])
#     print("Content Preview:", m["content"][:200], "...")


# context-building

def build_context_text(metadatas):
    context_parts = []
    for i, m in enumerate(metadatas):
        title = m.get("title", f"Chunk {i+1}")
        content = m.get("content", "")
        context_parts.append(f"[{i+1}] {title}\n{content}")
    
    context_text = "\n\n---\n\n".join(context_parts)
    return context_text


# Checking the context text before sending to the LLM

# query = "How can I reset my password?"
# metadatas, docs = retrieve_context(query, collection, k=5)

# context_text = build_context_text(metadatas)

# print("\nGENERATED CONTEXT:\n")
# print(context_text)


SYSTEM_PROMPT = """
You are a strict, kind, and helpful support assistant for Swaraj Desk.

Language rules (very important):
- Always respond ONLY in the target language specified in the instruction.
- Ignore the language and script of the user's question.
- Ignore the language and script of the context text.
- Use the context ONLY for meaning, not for wording.
- Never switch language or script in the same answer.

RESPONSE LOGIC:
1. Provide answers ONLY from the given context. Never guess or hallucinate.

2. If the question is NOT related to Swaraj Desk (its services, policies, portal usage, registration, complaint workflow, verification, documents, login, helpline, or support):
    - Do NOT attempt to answer.
    - Reply: "I can only assist with information related to Swaraj Desk. For more assistance you can connect directly to our website support."
    - Then provide this support escalation link (same language as response):
      https://swarajdesk.in/support
    - End the answer.

3. If the question IS related to Swaraj Desk but the user expresses:
   - urgency, or
   - need to talk to a person, or
   - confusion even after the answer, or
   - follow-up details beyond what context provides
   Then:
     a) First answer normally using ONLY the context.
     b) Then add this line (same language as response):
        "If you need further real-time assistance from our team, you can connect directly with the administrator here: https://swarajdesk.in/admin-assist"

4. If context does not contain enough information to answer:
    - Tell user politely that the information is not available.
    - DO NOT fabricate details.
    - Then provide support link:
      https://swarajdesk.in/support

5. Tone:
    - Strictly professional, concise, and helpful.
    - Never provide emotional opinions or political/social commentary.

Supported output modes:
- english  = reply fully in English.
- hindi    = reply fully in Hindi, using Devanagari script only.
- hinglish = reply in Hindi language but written in English letters only (no Devanagari).
- odia     = reply fully in Odia, using Odia script only.
"""


def answer_user_query(user_query: str, collection, language: str = "english"):
    # 1) Retrieve context
    metadatas, _ = retrieve_context(user_query, collection, k=5)
    context_text = build_context_text(metadatas)

    # 2) Language instruction (target output language)
    lang = language.lower()

    if lang == "hindi":
        language_instruction = (
            "Target language: Hindi.\n"
            "You MUST reply fully in Hindi, using Devanagari script only.\n"
            "Do NOT use English words unless they are technical terms like 'OTP', 'login', 'ID'.\n"
            "Do NOT use English letters. Do not mix Hindi and English."
        )
    elif lang == "hinglish":
        language_instruction = (
            "Target language: Hinglish.\n"
            "You MUST reply in Hindi language but written ONLY with English letters.\n"
            "Do NOT use Devanagari script. Example style: 'aap login page par jaakar password reset kar sakte hain'.\n"
            "Do NOT switch to full English sentences."
        )
    elif lang == "odia":
        language_instruction = (
            "Target language: Odia.\n"
            "You MUST reply fully in Odia language using Odia script only.\n"
            "Do NOT mix English sentences except for mandatory technical terms like 'OTP' or 'ID'."
        )
    else:
        # default: english
        language_instruction = (
            "Target language: English.\n"
            "You MUST reply fully in natural, clear English.\n"
            "Do NOT mix other languages."
        )

    # 3) Build final system message by combining base rules + language rules
    system_message = SYSTEM_PROMPT + "\n\n" + language_instruction + """
Always follow these extra rules:
- Use the context text only to understand the facts.
- Do NOT copy large English sentences directly if target language is Hindi, Hinglish or Odia.
- Convert the meaning of the context into the target language and script.
"""

    # 4) Messages for the LLM
    messages = [
        {"role": "system", "content": system_message},
        {
            "role": "user",
            "content": (
                "User question:\n"
                f"{user_query}\n\n"
                "Context (for facts only, not for language or style):\n"
                f"{context_text}"
            ),
        },
    ]

    # 5) Call Groq model
    model = ChatGroq(model="openai/gpt-oss-120b", groq_api_key=Groq_api_key)
    response = model.invoke(messages)
    final_answer = response.content.strip()
    return final_answer




## adding a voice bot 








## TESTING 

# Interact in English with user

# reply = answer_user_query(
#     "How can I reset my password?",
#     collection,
#     language="english"
# )
# print(reply)


# Interact in hindi with user

reply = answer_user_query(
    "शिकायत कैसे दर्ज करें",
    collection,
    language="hindi"
)
print(reply)

# reply = answer_user_query(
#     "Password reset karne ka tarika kya hai?",
#     collection,
#     language="hinglish"
# )
# print(reply)


## FINAL TESTING
user_question = "How can I reset my password?"
reply = answer_user_query(user_question, collection)

print("User:", user_question)
print("Bot :", reply)
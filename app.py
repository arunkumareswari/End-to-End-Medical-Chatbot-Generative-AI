from flask import Flask, render_template, jsonify, request
from src.helper import download_hugging_face_embeddings
from langchain_pinecone import PineconeVectorStore

# 🟢 IMPORTANT: use ChatGroq instead of OpenAI
from langchain_groq import ChatGroq

from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from src.prompt import *   # system_prompt, etc.
import os

app = Flask(__name__)

load_dotenv()

PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')   # 🔁 new variable

# set env for pinecone, groq (optional but okay)
os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY
os.environ["GROQ_API_KEY"] = GROQ_API_KEY

# ---------- Embeddings & Retriever ----------
embeddings = download_hugging_face_embeddings()

index_name = "healthsync-index"

docsearch = PineconeVectorStore.from_existing_index(
    index_name=index_name,
    embedding=embeddings
)

retriever = docsearch.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 3}
)

# ---------- LLM (Groq) ----------
llm = ChatGroq(
    groq_api_key=GROQ_API_KEY,
    model_name="llama-3.3-70b-versatile",
    temperature=0.3,
    max_tokens=500,
)

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        ("human", "{input}"),
    ]
)

question_answer_chain = create_stuff_documents_chain(llm, prompt)
rag_chain = create_retrieval_chain(retriever, question_answer_chain)


# ---------- Flask Routes ----------
@app.route("/")
def index():
    return render_template('chat.html')


@app.route("/get", methods=["GET", "POST"])
def chat():
    msg = request.form["msg"]
    print("User:", msg)

    try:
        response = rag_chain.invoke({"input": msg})
        answer = response["answer"]
    except Exception as e:
        print("Error from RAG chain:", e)
        answer = "Sorry, I'm facing a technical issue talking to the AI model right now."

    print("Response:", answer)
    return str(answer)


@app.route("/health", methods=["GET"])
def health():
    """
    Simple health endpoint used by the client to detect
    whether the Flask server / backend is reachable.
    Returns JSON {"status":"ok"} when the server is up.
    """
    return jsonify(status="ok"), 200

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080, debug=True)

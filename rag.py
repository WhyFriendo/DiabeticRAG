import os
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_openrouter import ChatOpenRouter
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
VECTOR_STORE_PATH = "faiss_index"

load_dotenv()


def build_rag_system(csv_path: str):
    """Loads CSV, creates vector store, and saves it locally."""
    print(f"Loading data from {csv_path}...")
    loader = CSVLoader(file_path=csv_path, encoding="utf-8", csv_args={
        'delimiter': ','
    })
    data = loader.load()

    print("Generating embeddings and building vector store...")
    embeddings = OpenAIEmbeddings(
        api_key=os.environ.get("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        model="openai/text-embedding-3-small"
    )


    vectorstore = FAISS.from_documents(data, embeddings)
    vectorstore.save_local(VECTOR_STORE_PATH)
    print(f"Vector store saved to {VECTOR_STORE_PATH}")
    return vectorstore

def get_rag_chain():
    """Returns the QA chain configured with the loaded vector store."""
    if not os.path.exists(VECTOR_STORE_PATH):
        raise FileNotFoundError("Vector store not found. Please upload/build from CSV first.")

    embeddings = OpenAIEmbeddings(
        api_key=os.environ.get("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        model="openai/text-embedding-3-small"
    )
    vectorstore = FAISS.load_local(VECTOR_STORE_PATH, embeddings, allow_dangerous_deserialization=True)

    retriever = vectorstore.as_retriever(search_kwargs={"k": 10})

    llm = ChatOpenRouter(
        api_key=os.environ.get("OPENROUTER_API_KEY"),
        # base_url="https://openrouter.ai/api/v1",
        model="deepseek/deepseek-v4-flash",
        temperature=0
    )

    system_prompt = (
        "You are an empathetic and helpful AI assistant specialized in analyzing diabetic CareLink data. "
        "Use the provided context containing the user's continuous glucose monitoring (CGM) and pump data "
        "to answer their questions. Provide insights, identify patterns, and highlight key points. "
        "At the beginning of conversation remind the user that you are an AI and they should consult a doctor for medical advice."
        "Don't use the internal data labels, talk to the user as to a non-technical person. If you are unsure about the answer, say 'I don't know' instead of making up an answer. "
        "Context: {context}"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    rag_chain = (
        {"context": retriever | format_docs, "input": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    return rag_chain

def answer_query(query: str) -> str:
    chain = get_rag_chain()
    response = chain.invoke(query)
    return response

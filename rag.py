import os
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_openrouter import ChatOpenRouter
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.documents import Document
from operator import itemgetter
import pandas as pd
from dotenv import load_dotenv
VECTOR_STORE_PATH = "faiss_index"

store = {}

def get_session_history(session_id: str):
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
    return store[session_id]

load_dotenv()


def build_rag_system(csv_path: str):
    """Loads CSV, creates vector store, and saves it locally."""
    print(f"Loading data from {csv_path}...")
    
    df = pd.read_csv(csv_path, skiprows=6, low_memory=False)
    
    docs = []
    print("Converting tabular data to narrative format...")
    for index, row in df.iterrows():
        date = str(row.get('Date', ''))
        time = str(row.get('Time', ''))
        
        if pd.isna(row.get('Date')) or pd.isna(row.get('Time')):
            continue
            
        narrative_parts = []
        metadata = {"date": date, "time": time}
        
        def get_num(col):
            val = row.get(col)
            if pd.isna(val):
                return None
            try:
                return float(val)
            except ValueError:
                return None

        sg = get_num('Sensor Glucose (mg/dL)')
        if sg is not None:
            narrative_parts.append(f"Sensor glucose was {sg} mg/dL.")
            metadata["sensor_glucose"] = sg
            
        bg = get_num('BG Reading (mg/dL)')
        if bg is not None:
            narrative_parts.append(f"Blood glucose reading was {bg} mg/dL.")
            metadata["bg_reading"] = bg
            
        bolus_vol = get_num('Bolus Volume Delivered (U)')
        if bolus_vol is not None and bolus_vol > 0:
            b_type = str(row.get('Bolus Type', 'normal'))
            if pd.isna(row.get('Bolus Type')):
                b_type = "normal"
            narrative_parts.append(f"Delivered a {b_type} bolus of {bolus_vol} units.")
            metadata["bolus_delivered"] = bolus_vol
            
        carbs = get_num('BWZ Carb Input (exchanges)')
        if carbs is not None and carbs > 0:
            narrative_parts.append(f"Patient consumed {carbs} exchanges of carbs.")
            metadata["carbs"] = carbs
            
        basal = get_num('Basal Rate (U/h)')
        if basal is not None:
            narrative_parts.append(f"Basal rate was set to {basal} U/h.")
            metadata["basal_rate"] = basal
            
        alert = row.get('Alert')
        if pd.notna(alert) and str(alert).strip() and str(alert).strip() != 'Alert':
            narrative_parts.append(f"Pump issued an alert: {alert}.")
            metadata["alert"] = str(alert)

        if narrative_parts:
            narrative = f"On {date} at {time}: " + " ".join(narrative_parts)
            docs.append(Document(page_content=narrative, metadata=metadata))

    print(f"Generated {len(docs)} documents.")

    print("Generating embeddings and building vector store...")
    embeddings = OpenAIEmbeddings(
        api_key=os.environ.get("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        model="openai/text-embedding-3-small"
    )

    vectorstore = FAISS.from_documents(docs, embeddings)
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
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
    ])

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    rag_chain = (
        RunnablePassthrough.assign(context=itemgetter("input") | retriever | format_docs)
        | prompt
        | llm
        | StrOutputParser()
    )

    conversational_chain = RunnableWithMessageHistory(
        rag_chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
    )

    return conversational_chain

def answer_query(query: str, session_id: str = "default") -> str:
    chain = get_rag_chain()
    response = chain.invoke(
        {"input": query},
        config={"configurable": {"session_id": session_id}}
    )
    return response

def answer_query_stream(query: str, session_id: str = "default"):
    chain = get_rag_chain()
    for chunk in chain.stream(
        {"input": query},
        config={"configurable": {"session_id": session_id}}
    ):
        yield chunk

async def answer_query_astream(query: str, session_id: str = "default"):
    chain = get_rag_chain()
    async for chunk in chain.astream(
        {"input": query},
        config={"configurable": {"session_id": session_id}}
    ):
        yield chunk
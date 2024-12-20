import streamlit as st
from langchain.chains import LLMChain
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain.embeddings.sentence_transformer import SentenceTransformerEmbeddings
from langchain_chroma import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.prompts import PromptTemplate
from langchain_community.llms import HuggingFaceHub
from langchain.retrievers.multi_query import MultiQueryRetriever
import os, logging
from dotenv import load_dotenv

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

load_dotenv()

# Load API key from Streamlit secrets
HUGGINGFACEHUB_API_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN")

if HUGGINGFACEHUB_API_TOKEN == None:
    HUGGINGFACEHUB_API_TOKEN = st.secrets["HUGGINGFACEHUB_API_TOKEN"]

os.environ["HUGGINGFACEHUB_API_TOKEN"] = HUGGINGFACEHUB_API_TOKEN

loader = PyPDFDirectoryLoader(path='documents/', glob="**/*.pdf")
pdfs = loader.load()

splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
docs = splitter.split_documents(pdfs)

embeddings = SentenceTransformerEmbeddings(model_name='all-MiniLM-L6-v2')
db = Chroma(persist_directory='./db', embedding_function=embeddings)

model_path = "openai-community/gpt2"

llm = HuggingFaceHub(repo_id=model_path, model_kwargs={'temperature': 0.5, 'max_length': 200})

template = """
You are an AI assistant. You have access to the content of several PDF documents from Google, Uber and Tesla. Compare the information from these documents to answer the following question: Question: {question}
"""

prompt_template = PromptTemplate(template=template, input_variables=['question'])

retriever = MultiQueryRetriever.from_llm(retriever=db.as_retriever(), llm=llm, prompt=prompt_template)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("langchain.retrievers.multi_query").setLevel(logging.INFO)

llm_chain = LLMChain(llm=llm, prompt=prompt_template)

# UI Enhancements
st.title("🚀 Chatbot")
st.markdown("Your smart assistant for comparing document insights! 🌟")

st.markdown(
    """
    <style>
    .chat-user {
        color: #4caf50;
        font-weight: bold;
    }
    .chat-bot {
        color: #2196f3;
        font-weight: bold;
    }
    .chat-input {
        width: 100%;
        padding: 15px;
        font-size: 16px;
        border-radius: 10px;
        border: 1px solid #ddd;
    }
    .submit-button {
        background-color: #4caf50;
        color: white;
        padding: 10px 20px;
        border: none;
        border-radius: 5px;
        cursor: pointer;
        font-size: 16px;
    }
    .submit-button:hover {
        background-color: #45a049;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Initialize session state for storing chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Input box with a submit button
col1, col2 = st.columns([4, 1])
with col1:
    query = st.text_input("Type your query here:", key="input_query", placeholder="Hello, I am a ChatBot. How may I help you?", label_visibility="collapsed")
with col2:
    submit = st.button("Submit", key="submit_button")

if submit and query:
    with st.spinner("Processing your query..."):
        docs = retriever.get_relevant_documents(query=query)
        context = "\n---------------\n".join([d.page_content for d in docs])
        output = llm_chain(inputs={"question": query, "context": context})
        response = str(output['text'].split('Answer: ')[1].strip())

        # Add user query and bot response to chat history
        st.session_state.messages.append({"user": query, "bot": response})

# Display chat history without a box around the response
for message in st.session_state.messages:
    st.markdown(f"**You:** {message['user']}")
    st.markdown(f"**Bot:** {message['bot']}")
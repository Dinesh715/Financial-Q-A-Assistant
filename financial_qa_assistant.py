import streamlit as st
import pandas as pd
import pdfplumber
import tempfile
from pathlib import Path
import requests

st.set_page_config(
    page_title="Financial Document Q&A Assistant",
    page_icon="📊",
    layout="wide"
)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "processed_text" not in st.session_state:
    st.session_state.processed_text = ""
if "document_type" not in st.session_state:
    st.session_state.document_type = None

def extract_text_from_pdf(uploaded_file):
    text = ""
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def extract_text_from_excel(uploaded_file):
    text = ""
    try:
        excel_file = pd.ExcelFile(uploaded_file)
        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(uploaded_file, sheet_name=sheet_name)
            text += f"Sheet: {sheet_name}\n"
            text += df.to_string() + "\n\n"
    except Exception as e:
        st.error(f"Error reading Excel file: {e}")
    return text

def process_uploaded_file(uploaded_file):
    file_type = uploaded_file.type
    try:
        if file_type == "application/pdf":
            text = extract_text_from_pdf(uploaded_file)
            doc_type = "PDF"
        elif file_type in ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                          "application/vnd.ms-excel"]:
            text = extract_text_from_excel(uploaded_file)
            doc_type = "Excel"
        else:
            st.error("Unsupported file format")
            return None, None
        
        return text, doc_type
    except Exception as e:
        st.error(f"Error processing file: {e}")
        return None, None

def query_ollama(prompt, context=""):
    try:
        full_prompt = f"""
        You are a financial analyst assistant. Based on the following financial document content, answer the user's question.
        
        Financial Document Content:
        {context}
        
        User Question: {prompt}
        
        Provide a concise, accurate answer based solely on the provided financial document. 
        If the information is not available in the document, state that clearly.
        """
        
        url = "http://localhost:11434/api/generate"
        
        payload = {
            "model": "mistral",
            "prompt": full_prompt,
            "stream": False
        }
        
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            return response.json()["response"]
        else:
            return f"Error: Unable to get response from Ollama. Status code: {response.status_code}"
    
    except Exception as e:
        return f"Error querying language model: {str(e)}"

def main():
    st.title("📊 Financial Document Q&A Assistant")
    st.markdown("Upload financial documents (PDF or Excel) and ask questions about the data.")
    
    with st.sidebar:
        st.header("Document Upload")
        uploaded_file = st.file_uploader(
            "Choose a PDF or Excel file",
            type=['pdf', 'xlsx', 'xls'],
            help="Supported formats: PDF, Excel (XLSX, XLS)"
        )
        
        if uploaded_file is not None:
            with st.spinner("Processing document..."):
                processed_text, doc_type = process_uploaded_file(uploaded_file)
                
                if processed_text:
                    st.session_state.processed_text = processed_text
                    st.session_state.document_type = doc_type
                    st.success(f"{doc_type} document processed successfully!")
                    
                    st.subheader("Document Preview")
                    if doc_type == "PDF":
                        preview_text = processed_text[:500] + "..." if len(processed_text) > 500 else processed_text
                        st.text_area("Extracted Text", preview_text, height=200)
                    else:
                        try:
                            df = pd.read_excel(uploaded_file, sheet_name=0)
                            st.dataframe(df.head(5))
                        except:
                            preview_text = processed_text[:500] + "..." if len(processed_text) > 500 else processed_text
                            st.text_area("Extracted Text", preview_text, height=200)
                else:
                    st.error("Failed to process the document.")
        
        st.markdown("---")
        st.info("""
        **Note:** 
        - Ensure Ollama is running locally on port 11434
        - Supported models: mistral, llama2, or other financial-focused models
        - Documents are processed locally for privacy
        """)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Document Status")
        if st.session_state.document_type:
            st.success(f"{st.session_state.document_type} document loaded")
            st.metric("Extracted Text Length", f"{len(st.session_state.processed_text)} characters")
        else:
            st.warning("No document uploaded")
        
        st.subheader("Example Questions")
        st.markdown("""
        - What was the total revenue?
        - How much did we spend on marketing?
        - What are our largest expenses?
        - What is the net profit?
        - Show me the quarterly growth trends
        - Compare expenses between quarters
        """)
    
    with col2:
        st.subheader("Chat with Your Financial Data")
        
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        if prompt := st.chat_input("Ask a question about your financial document..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = query_ollama(prompt, st.session_state.processed_text)
                    st.markdown(response)
            
            st.session_state.messages.append({"role": "assistant", "content": response})
        
        if st.button("Clear Conversation"):
            st.session_state.messages = []
            st.rerun()

if __name__ == "__main__":
    main()
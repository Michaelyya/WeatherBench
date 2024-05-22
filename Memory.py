import os
from langchain.agents import AgentType
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_openai import OpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Pinecone as PineconeStore 
from langchain.chains import RetrievalQA
from pinecone import Pinecone, ServerlessSpec
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_openai import OpenAIEmbeddings
from openai import OpenAI

client = OpenAI()
import pinecone
from GPT_model import analyze_topics
from dotenv import load_dotenv
load_dotenv()

pinecone_api = os.environ.get("PINECONE_API_KEY")
api_key = os.environ.get("PINECONE_API_KEY")
pc = Pinecone(api_key="pinecone_api")

client = OpenAI(
  api_key=os.environ.get("OPENAI_API_KEY")
)

index_name = "geog-research"
if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name, 
        dimension=1536,  # Adjust the dimension to match your embeddings
        metric='cosine',  # Choose the metric that suits your use case
        spec=ServerlessSpec(
            cloud='aws',  # or 'gcp' depending on your preference or requirements
            region='us-east-1'  # Choose the region closest to you or your users
        )
    )

embeddings = OpenAIEmbeddings(openai_api_key=os.environ.get("OPENAI_API_KEY"))

index = pc.Index(index_name)

def generate_embeddings(text):
    """
    Generates embeddings using OpenAI's API.
    """
    try:
        # Assuming `text` is a non-empty string
        response = client.embeddings.create( model="text-embedding-ada-002",input=text)
        # Extracting the first embedding vector
        return response.data[0].embedding
    except Exception as e:
        print(f"Error generating embeddings: {e}")
        return None

def upsert_to_pinecone(data):
    for item in data['info']:
        vulnerabilities = item.get('Vulnerabilities', '').strip()
        responses = item.get('Resilience and Responses', '').strip()

        if vulnerabilities: # Checks if the string is non-empty
            vulnerability_id = f"vuln-{os.urandom(4).hex()}"  # Unique ID for the entry
            vulnerability_embedding = generate_embeddings(vulnerabilities)
            if vulnerability_embedding:
                index.upsert(vectors=[(vulnerability_id, vulnerability_embedding)])
                print(f"Inserted vulnerabilities into Pinecone with ID: {vulnerability_id}")

        if responses: # Checks if the string is non-empty
            response_id = f"resp-{os.urandom(4).hex()}"  # Unique ID for the entry
            response_embedding = generate_embeddings(responses)
            if response_embedding:
                index.upsert(vectors=[(response_id, response_embedding)])
                print(f"Inserted responses into Pinecone with ID: {response_id}")

def search_similar_texts(query_text, top_k=5):
    query_embedding = generate_embeddings(query_text)
    if query_embedding:
        results = index.query(queries=[query_embedding], top_k=top_k)
        return results
    else:
        return {"matches": []}

def generate_response(contexts):
    """ Generate a response based on retrieved contexts using a language model. """
    context = " ".join(contexts)
    prompt = f"Given the following information: {context}, summarize the key points and answer the user's query."
    response = client.Completion.create(engine="davinci", prompt=prompt, max_tokens=150)
    return response.choices[0].text

def rag_system(query):
    similar_docs = search_similar_texts(query)
    if similar_docs['matches']:
        contexts = [doc['metadata'].get('text', '') for doc in similar_docs['matches']]
        response = generate_response(contexts)
        return response
    else:
        return "No relevant information found based on your query."

# Test Case
def test_rag_system():
    query = "What are the vulnerabilities and responses related to heatwaves?"
    response = rag_system(query)
    print("Response:", response)
    
    # Asserting the expected response
    expected_keywords = ["vulnerability", "heatwaves", "deaths", "government actions", "health sector adaptation", "inequalities", "long-term strategies"]
    for keyword in expected_keywords:
        assert keyword in response, f"Expected keyword '{keyword}' not found in the response."

if __name__ == "__main__":
    test_rag_system()

if __name__ =="__main__":
    file = "blog/cold _English_historical_ML_corpus.txt"
    topics = [
        "weather",
    ]
    data = analyze_topics(file,topics)
    print(analyze_topics(file,topics))
    upsert_to_pinecone(data)



# def search(query, texts, text_embeddings):
#     query_embedding = OpenAIEmbeddings.embed_query(query)
#     similarities = [np.dot(query_embedding, text_emb) / (np.linalg.norm(query_embedding) * np.linalg.norm(text_emb)) for text_emb in text_embeddings]
#     max_index = np.argmax(similarities)
#     return texts[max_index]





    # text_embeddings = [embeddings.embed_query(text) for text in texts]
    # query = "Please give me some summarization about the extreme weather information"
    # result = search (query, texts, text_embeddings)


    # docsearch = PineconeStore.from_documents(text, embeddings, index_name=index_name)
    # qa = RetrievalQA.from_chain_type(llm=OpenAI(), chain_type="stuff", retriever=docsearch.as_retriever())



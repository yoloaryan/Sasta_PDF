from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from database import get_vectorstore

llm = ChatGroq(
    model_name="openai/gpt-oss-120b",
    temperature=0.2,
)

prompt = ChatPromptTemplate.from_messages([
    ("system", """
You are SastaPDF AI, an intelligent document assistant.

Use ONLY the supplied document context.
Do not use outside knowledge or hallucinate.
If the answer is not present in the context, say exactly:
"I could not find the answer in the document."

Give a clear, useful answer. When possible, refer to page numbers.

Document context:
{context}
"""),
    ("human", "Question:\n{question}")
])

def ask_question(question: str, document_id: str | None = None):
    vectorstore = get_vectorstore()

    kwargs = {
        "k": 5,
        "fetch_k": 15,
        "lambda_mult": 0.5,
    }

    if document_id:
        kwargs["filter"] = {"document_id": document_id}

    docs = vectorstore.max_marginal_relevance_search(
        question,
        **kwargs
    )

    if not docs:
        return {
            "answer": "I could not find the answer in the document.",
            "sources": [],
        }

    context_parts = []

    for doc in docs:
        page = doc.metadata.get(
            "page_number",
            doc.metadata.get("page", 0) + 1
        )
        context_parts.append(
            f"[Page {page}]\n{doc.page_content}"
        )

    context = "\n\n".join(context_parts)

    final_prompt = prompt.invoke({
        "context": context,
        "question": question,
    })

    response = llm.invoke(final_prompt)

    sources = []
    seen = set()

    for doc in docs:
        page = doc.metadata.get(
            "page_number",
            doc.metadata.get("page", 0) + 1
        )
        filename = doc.metadata.get(
            "filename",
            "Unknown"
        )

        key = (filename, page)

        if key not in seen:
            seen.add(key)
            sources.append({
                "filename": filename,
                "page": page,
                "document_id": doc.metadata.get(
                    "document_id"
                ),
            })

    return {
        "answer": response.content,
        "sources": sources
    }

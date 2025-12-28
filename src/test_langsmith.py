from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

prompt = ChatPromptTemplate.from_messages(
    [("user", "Say hello from Gemini")]
)

model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",   # or another Gemini model
    temperature=0.2,
    api_key="AIzaSyAN84qSqGPxO6jK6Kj9SvqxUZvEqtg73Yk",
)

chain = prompt | model

print(chain.invoke({}))

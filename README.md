# VizBot: Graph Generation Using Multi-Agent LLM Models to Derive Space Insights

A dissertation project implementing **VizBot**, a natural language to SQL chatbot that connects to PostgreSQL, generates interactive visualizations, and derives insights using Large Language Models (LLMs).

---

## 🚀 Features
- **Natural Language Queries** → Translates user queries into SQL automatically.
- **Interactive Visualizations** → Generates charts (line, bar, box, heatmap) with Plotly.
- **Insight Generation** → Uses OpenAI GPT models for textual interpretations.
- **User Authentication** → Secure login system with hashed passwords.
- **Extensible Modular Design** → Multi-agent architecture for easy enhancements.

---

## 📂 Project Structure
project-root/
│── agents/ # Modular agent scripts (planner, retriever, etc.)
│── database/ # Database schema and models
│── llm/ # LLM connectors (OpenAI integration)
│── scripts/ # Utility scripts (e.g., user creation)
│── utils/ # Authentication, helpers
│── data/ # (Optional) Sample datasets
│── app.py # Main entry point (Streamlit app)
│── requirements.txt # Project dependencies
│── .env # Environment variables (not shared in repo)
│── README.md # Project documentation
│── .gitignore # Ignore sensitive/unnecessary files


---

## ⚙️ Installation

1. Clone the repository:
   ```bash
   git clone git@github.com:your-username/vizbot.git
   cd vizbot

2. Create & activate virtual environment:
    python -m venv venv
    source venv/bin/activate   # (Linux/Mac)
    venv\Scripts\activate      # (Windows)

3. Install dependencies:
    pip install -r requirements.txt

🔑 Environment Setup

Create a .env file in project root:

    DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/smartvizdb
    OPENAI_API_KEY=your_openai_api_key
    OPENAI_MODEL=gpt-3.5-turbo
    LANGCHAIN_TRACING_V2=true
    LANGCHAIN_API_KEY=your_langchain_key
    LANGCHAIN_PROJECT=vizbot

⚠️ Do not share your .env file publicly.

▶️ Running the App

Run the Streamlit application:
    streamlit run app.py

The app will launch in your browser at:
👉 http://localhost:8501

👥 User Authentication

Before first use, create a user via:
python scripts/create_user.py <username> <password>

📊 Example Query Scenarios

"Show CO₂ utilization of Seminar-51 between 2025-05-05 and 2025-05-12"
"Compare temperature and humidity in Lecture Theatre-4"
"Top 3 rooms with highest occupancy"

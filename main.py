import streamlit as st
import pandas as pd
import numpy as np
import pymongo as pm
import dotenv
from langlearncopilot.generators import generate_unique_words
from langlearncopilot.parsers import get_text_from_webpage
from langlearncopilot.utilities.save_anki_format import save_unique_words
import pandas as pd
import os
from uuid import uuid4
from datetime import datetime

st.set_page_config(
    page_title="LangLearnCoPilot",
    page_icon="./favicon.png", # Source: <a target="_blank" href="https://icons8.com/icon/103187/language">Language</a> icon by <a target="_blank" href="https://icons8.com">Icons8</a>
    layout="centered",
    initial_sidebar_state="expanded"
)

@st.cache_data
def load_env():
    dotenv.load_dotenv()

@st.cache_resource
def database_connection():
    client = pm.MongoClient(os.getenv("MONGO_URI"))
    db = client["langlearncopilot"]
    return db


# Setup global variables
load_env()
DB_COLLECTION = database_connection()
MACHINE_ID = os.getenv("MACHINE_ID")

def register_events(event:dict):
    global DB_COLLECTION
    # Add time
    event["time"] = datetime.now()
    # convert time to string
    event["time"] = event["time"].strftime("%Y-%m-%d %H:%M:%S")
    # Add session ID
    event["session_id"] = st.session_state["session_id"]
    # Add machine ID
    event["machine_id"] = MACHINE_ID
    DB_COLLECTION["events"].insert_one(event)

@st.cache_data
def get_text_from_website(url:str, language:str="english"):
    text = get_text_from_webpage(url)
    unique_words = generate_unique_words(text, language=language)
    return unique_words

@st.cache_data
def prepare_data_to_download(unique_words:dict):
    data_to_download = save_unique_words(unique_words)
    data_to_download_csv = pd.DataFrame(data_to_download).to_csv(index=False, header=False)
    return data_to_download_csv

def formulate_as_dataframe(unique_words:dict):
    """
    Convert a dictionary of "original word": "translation" into a dataframe
    """
    df = pd.DataFrame.from_dict(unique_words, orient="index")
    df = df.reset_index()
    df.columns = ["original", "translation"]

    return df

def sidebar():
    st.sidebar.title("About")
    st.sidebar.info(
        """
        This app is a demo of the [LangLearnCoPilot](https://github.com/osm3000/LangLearnCopilot) - a tool to help you learn a new language.
        To read more about the story behind this, please visit <LINK TO BLOG POST>.
        Developed by [Omar Mohammed](https://www.linkedin.com/in/omar-mohammed3000/).
        """,icon="🔥"
    )

    with st.sidebar.form("consent_form"):
        st.info(
            """
            Are you okay if I collect usage data to improve this app? This is completely anonymous and no personal information is collected. It is mainly for my research.
            """, icon="❓"
        )
        consent_value = st.radio("Consent to the data collection", ("Yes", "No"), index=0, key="consent", captions=("Yes I consent to the data collection", "No, I don't consent"))
        st.write(f"Consent value: {consent_value}")
        submit_consent_button = st.form_submit_button(label="Submit Consent", type="primary")
        if submit_consent_button: # TODO: This is not working properly yet
            # st.session_state.consent = consent_value
            register_events({
                "type": "consent_submitted",
                "consent": consent_value
            })



def main():
    global DB_COLLECTION
    st.title("Get all the words from a webpage")

    # Setup a session ID
    if "session_id" not in st.session_state:
        st.session_state["session_id"] = str(uuid4())
        # Register an event
        register_events({
            "type": "session_start",
            "session_id": st.session_state["session_id"]
        })
    if "consent" not in st.session_state:    
        st.session_state["consent"] = "Yes"


    # Show the sidebar
    sidebar()

    with st.form("url_form", clear_on_submit=True):
        url = st.text_input("Enter a URL of a webpage")
        language = st.selectbox("Select the text language", ["french", "spanish", "german", "italian"], index=0)
        submit_button = st.form_submit_button(label="Submit", type="primary", on_click=register_events, kwargs={
            "event": {
                "type": "submit",
                "url": url,
                "language": language,
            }
        })
    if submit_button:
        unique_words = None
        with st.status("Processing..."):
            unique_words = get_text_from_website(url, language=language)
        df = formulate_as_dataframe(unique_words)
        
        columns = st.columns(2)
        with columns[0]:
            st.write(df)
            st.write(f"Number of unique words: {len(unique_words)}")
        with columns[1]:
            data_to_download = prepare_data_to_download(unique_words)
            download_btn = st.download_button(
                label="Download data as CSV",
                data=data_to_download,
                file_name='flashcards.csv',
                mime='text/csv',
                on_click=register_events,
                kwargs={
                    "event": {
                        "type": "download",
                        "url": url,
                        "language": language,
                    }
                }
            )

    # Feedback form
    st.write("If you have any feedback, please let me know!")
    with st.form("feedback_form", clear_on_submit=True):
        feedback = st.text_area("Feedback")
        name = st.text_input("Name (optional)", value="Anonymous")
        email = st.text_input("Email (optional)", value="Anonymous")
        submit_button = st.form_submit_button(label="Submit", type="primary", on_click=register_events, kwargs={
            "event": {
                "type": "feedback",
                "feedback": feedback,
                "name": name,
                "email": email
            }
        })
    if submit_button:
        st.write("Thank you for your feedback!")
        


if __name__ == "__main__":
    main()
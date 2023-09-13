import streamlit as st
import pandas as pd
import numpy as np
import pymongo as pm
import dotenv
from langlearncopilot.generators import generate_unique_words, generate_phrases
from langlearncopilot.parsers import get_text_from_webpage
from langlearncopilot.utilities.save_anki_format import save_unique_words
from langlearncopilot.llm_calls import set_credentials
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
    set_credentials.set_openai_key(os.getenv("OPENAI_KEY", st.secrets["OPENAI_KEY"]))

@st.cache_resource
def database_connection():
    client = pm.MongoClient(os.getenv("MONGO_URI", st.secrets["MONGO_URI"]))
    db = client["langlearncopilot"]
    return db


# Setup global variables
load_env()
DB_COLLECTION = database_connection()
MACHINE_ID = os.getenv("MACHINE_ID", st.secrets["MACHINE_ID"])

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

    if st.session_state["consent"]: # Only save if consent is given
        DB_COLLECTION["events"].insert_one(event)

@st.cache_data
def get_text_from_website(url:str, language:str="english"):
    text = get_text_from_webpage(url)
    st.write(text)
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
            Are you okay if I collect usage data to improve this app? This is completely anonymous and no personal information is collected. It is mainly for my research. Please remember that, since there are not accounts, the answer will be reset if you refresh the page.
            """, icon="❓"
        )
        consent_value = st.radio("Consent to the data collection", ("Yes", "No"), index=0, key="radio_consent", captions=("Yes I consent to the data collection", "No, I don't consent"))
        st.write(f"Consent value: {consent_value}")
        submit_consent_button = st.form_submit_button(label="Submit Consent", type="primary")
        if submit_consent_button: # TODO: This is not working properly yet
            
            bool_consent_value = True if consent_value == "Yes" else False
            st.session_state["consent"] = bool_consent_value
            register_events({
                "type": "consent_submitted",
                "consent": bool_consent_value
            })
            st.write(f"Your consent has been submitted: {consent_value}")



def main():
    global DB_COLLECTION
    st.image("./logo.png", width=200)
    st.title("Get all the words from a webpage")

    # Setup a session ID
    if "consent" not in st.session_state:    
        st.session_state["consent"] = True
        st.experimental_rerun()
    if "session_id" not in st.session_state:
        st.session_state["session_id"] = str(uuid4())
        # Register an event
        register_events({
            "type": "session_start",
            "session_id": st.session_state["session_id"]
        })


    # Show the sidebar
    sidebar()

    with st.form("webpage_parsing"):
        st.info(
            """
            Feature 1: the app will extract all the unique words from a webpage and save them in a CSV file. You can then use this file to create flashcards to help you learn the language.
            """, icon="ℹ️"
        )
        url = st.text_input("Enter a URL of a webpage")
        language = st.selectbox("Select the text language", ["french", "spanish", "german", "italian"], index=0)
        webpage_parsing_submit_button = st.form_submit_button(label="Submit", type="primary", on_click=register_events, kwargs={
            "event": {
                "type": "submit",
                "url": url,
                "language": language,
            }
        })
    if webpage_parsing_submit_button:
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
                file_name='words_flashcards.csv',
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


    with st.form("Generate Phrases"):
        st.info(
            """
            Feature 2: For each word, generate a phrase that uses that word. This will help you understand the word in context.
            """, icon="ℹ️"
        )
        unique_words = st.text_area("Enter the unique words (one word per line) - Max 3 words")
        language_phrases = st.selectbox("Select the text language", ["french", "spanish", "german", "italian"], index=0)
        generate_phrases_submit_button = st.form_submit_button(label="Submit", type="primary", on_click=register_events, kwargs={
            "event": {
                "type": "generate_phrases",
                "language": language,
                "unique_words": unique_words,
            }
        })
    if generate_phrases_submit_button:
        st.write("Generating phrases...")
        list_of_unique_words = unique_words.split("\n")
        if len(list_of_unique_words) > 3: # Only take the first 3 words
            list_of_unique_words = list_of_unique_words[:3]
        final_results = []
        for word in list_of_unique_words:
            st.write(f"Word: {word}")
            final_results.append(pd.DataFrame(generate_phrases(word, language=language_phrases)))
        final_results_df = pd.concat(final_results).reset_index(drop=True)

        columns_2 = st.columns(2)
        with columns_2[0]:
            st.write(final_results_df)
        with columns_2[1]:
            download_btn = st.download_button(
                label="Download data as CSV",
                data=final_results_df.to_csv(index=False, header=False),
                file_name='phrases_flashcards.csv',
                mime='text/csv',
                on_click=register_events,
                kwargs={
                    "event": {
                        "type": "download_phrases",
                        "url": url,
                        "language": language,
                    }
                }
            )


    # Feedback form
    with st.form("feedback_form", clear_on_submit=True):
        st.info("If you have any feedback, please let me know!", icon="📝")
        feedback = st.text_area("Feedback")
        name = st.text_input("Name (optional)", value="Anonymous")
        email = st.text_input("Email (optional)", value="Anonymous")
        feedback_form_submit_button = st.form_submit_button(label="Submit", type="primary", on_click=register_events, kwargs={
            "event": {
                "type": "feedback",
                "feedback": feedback,
                "name": name,
                "email": email
            }
        })
    if feedback_form_submit_button:
        st.write("Thank you for your feedback!")
        


if __name__ == "__main__":
    main()
import os
import io
import tempfile
import requests

import openai
import PyPDF2
import docx2txt
import streamlit as st
import speech_recognition as sr
from st_audiorec import st_audiorec
from streamlit_lottie import st_lottie

# 1) PAGE CONFIG
st.set_page_config(page_title="JobLens – Interview Assistant", layout="wide")

# 2) VALIDATE OPENAI API KEY
OPENAI_API_KEY = "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"
if not OPENAI_API_KEY:
    st.error("🚨 OpenAI API Key is missing! Please set it as an environment variable 'OPENAI_API_KEY'.")
    st.stop()
openai.api_key = OPENAI_API_KEY

# 3) MAIN PAGE TITLE & DESCRIPTION
st.title("JobLens – AI-Powered Interview Assistant")
# 4) LOAD A LOTTIE ANIMATION
def load_lottieurl(url: str):
    """
    Utility function to load a Lottie animation from a given URL.
    """
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

# Example Lottie from LottieFiles (replace with your own URL if desired)
LOTTIE_URL = "https://lottie.host/cc830714-aef0-461a-af23-87ee3713ebee/1lhZdJMp97.json"
lottie_animation = load_lottieurl(LOTTIE_URL)
if lottie_animation:
        st_lottie(lottie_animation, height=180, key="interview_lottie")
else:
        st.warning("⚠️ Could not load Lottie animation. Check the URL or your connection.")
st.markdown(
    """
    **JobLens** is an AI-powered interview system that can:
    - Conduct interviews
    - Analyze candidate responses
    - Provide objective evaluations
    
    Interviews are a key part of hiring, but they can often be biased or inconsistent. 
    With **JobLens**, we aim to streamline and improve the entire process.
    """
)
st.divider()


# 5) SIDEBAR LAYOUT
with st.sidebar:
    st.header("Interview Setup")
    
    # Inputs for job description, position, and CV
    job_desc = st.text_area("Job Description", height=100)
    job_position = st.text_input("Job Position", value="")
    uploaded_cv = st.file_uploader("Upload CV (PDF or DOCX)", type=["pdf", "docx"])
    
    # Button to generate questions
    generate_button = st.button("🚀 Generate Questions")

    # st.divider()

    # Display Lottie animation)

    st.markdown(
        """
        _Created by **JobLens**._
        """
    )

# 6) HELPER FUNCTIONS
def extract_text_from_file(uploaded_file):
    """
    Extract text from a PDF or DOCX file and return as a string.
    """
    if not uploaded_file:
        return ""
    text = ""
    file_type = uploaded_file.type

    try:
        if file_type == "application/pdf":
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            for page in pdf_reader.pages:
                page_text = page.extract_text() or ""
                text += page_text + "\n"
        elif file_type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                           "application/msword"]:
            with io.BytesIO(uploaded_file.read()) as tmp:
                text = docx2txt.process(tmp)
        else:
            st.warning("⚠️ Unsupported file type. Please upload PDF or DOCX.")
    except Exception as e:
        st.error(f"Error reading file: {e}")
    return text

def generate_interview_questions(resume_text, job_description, job_position, n=5):
    """
    Generate interview questions via OpenAI's ChatCompletion.
    """
    prompt = f"""
You are an AI assistant helping a recruiter interview a candidate.

Candidate's Resume:
{resume_text}

Job Description:
{job_description}

Position: {job_position}

Generate {n} direct, concise, and relevant interview questions.
Return them line by line with no extra explanation.
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful interview assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )
        output = response.choices[0].message.content.strip()
        questions = [line.strip("-• \t\r") for line in output.split("\n") if line.strip()]
        return questions
    except Exception as e:
        st.error(f"Error generating questions: {e}")
        return []

def transcribe_audio_to_text(audio_bytes):
    """
    Transcribe audio using SpeechRecognition + Google Web Speech API.
    """
    recognizer = sr.Recognizer()
    text_output = ""
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
            temp_audio.write(audio_bytes)
            temp_audio.flush()
            temp_name = temp_audio.name

        with sr.AudioFile(temp_name) as source:
            recognizer.adjust_for_ambient_noise(source)
            audio_data = recognizer.record(source)

        text_output = recognizer.recognize_google(audio_data)
    except Exception as e:
        text_output = f"Error transcribing audio: {e}"
    finally:
        if temp_name and os.path.exists(temp_name):
            os.remove(temp_name)
    return text_output

def evaluate_answer(answer, question):
    """
    Evaluate the candidate's answer using OpenAI ChatCompletion.
    Provide a rating (1-5) and short feedback.
    """
    if not answer.strip():
        return "⚠️ No answer provided."

    eval_prompt = f"""
You are an AI HR assistant.

Question: {question}
Candidate's answer: {answer}

Please rate the answer from 1 to 5 (5 = best) and provide concise feedback.
Return in this format:

Score: X
Feedback: <one or two sentences>
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an AI HR assistant evaluating interview answers."},
                {"role": "user", "content": eval_prompt},
            ],
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error in evaluation: {e}"

# 7) MAIN LOGIC: GENERATE QUESTIONS
if generate_button:
    if not job_desc.strip():
        st.sidebar.error("⚠️ Please provide a job description.")
    elif not job_position.strip():
        st.sidebar.error("⚠️ Please provide a job position.")
    elif not uploaded_cv:
        st.sidebar.error("⚠️ Please upload a CV.")
    else:
        cv_text = extract_text_from_file(uploaded_cv)
        with st.spinner("Generating interview questions..."):
            questions = generate_interview_questions(cv_text, job_desc, job_position, n=5)
            if questions:
                st.session_state["questions"] = questions
                st.session_state["question_index"] = 0
                st.session_state["feedback_list"] = []
                st.sidebar.success("✅ 5 questions generated! Scroll down to start the interview.")

# 8) INTERVIEW Q&A SECTION
if "questions" in st.session_state and st.session_state["questions"]:
    q_index = st.session_state["question_index"]
    questions = st.session_state["questions"]

    if q_index < len(questions):
        current_question = questions[q_index]
        st.markdown(f"### Question {q_index + 1} of {len(questions)}")
        st.markdown(f"**❓ {current_question}**")

        st.write("🎙️ **Record your answer below:**")
        audio_data = st_audiorec()

        if st.button("✅ Submit Answer"):
            if not audio_data:
                st.warning("Please record your answer before clicking submit.")
            else:
                with st.spinner("Transcribing your response..."):
                    answer_text = transcribe_audio_to_text(audio_data)
                st.write(f"**Transcribed Answer:** {answer_text}")

                with st.spinner("Evaluating your answer..."):
                    feedback = evaluate_answer(answer_text, current_question)

                st.session_state["feedback_list"].append((current_question, answer_text, feedback))

                # Move to next question
                st.session_state["question_index"] += 1
                st.rerun()

    else:
        st.success("✅ Interview complete! See your feedback below:")
        for i, (q, ans, fb) in enumerate(st.session_state["feedback_list"], start=1):
            st.markdown(f"**Q{i}:** {q}")
            st.markdown(f"- **Your Answer:** {ans}")
            st.markdown(f"- **Feedback:** {fb}")
            st.markdown("---")

        if st.button("🔄 Restart Interview"):
            del st.session_state["questions"]
            del st.session_state["question_index"]
            del st.session_state["feedback_list"]
            st.rerun()
else:
    st.info("Configure your interview in the sidebar and click 'Generate Questions' to begin.")

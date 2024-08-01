import streamlit as st
from chatbot import Chatbot
from utils import generate_followup_questions

def main():
    st.title("Women's Wellness AI Chatbot")

    # Initialize chat history and follow-up questions
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "followup_questions" not in st.session_state:
        st.session_state.followup_questions = []

    # Initialize chatbot
    chatbot = Chatbot()

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Display follow-up questions if available
    if st.session_state.followup_questions:
        st.write("Follow-up questions:")
        for question in st.session_state.followup_questions:
            if st.button(question):
                handle_user_input(question, chatbot)

    # React to user input
    if prompt := st.chat_input("What would you like to know about women's health and wellness?"):
        handle_user_input(prompt, chatbot)

    # Add feedback button
    st.sidebar.markdown("### We value your feedback!")
    feedback_url = "https://docs.google.com/forms/d/e/1FAIpQLSfZfHX0wwALRs87mRERfsDLiFIgpXkVuxLOCThZIci-H6L5qg/viewform?usp=sf_link"  # Replace with your actual Google Forms URL
    st.sidebar.markdown(f"[Provide Feedback]({feedback_url})")

def handle_user_input(prompt, chatbot):
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)

    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Get response from chatbot
    response = chatbot.get_response(prompt)

    if "Sources:" in response:
        # Split the response into summary and sources
        summary, sources = response.split("Sources:", 1)
        with st.chat_message("assistant"):
            st.markdown(summary.strip())
            st.markdown("\nSources:\n" + sources)
    else:
        st.chat_message("assistant").markdown(response)

    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})

    # Generate and store follow-up questions
    st.session_state.followup_questions = generate_followup_questions(response)

    # Clear the input box after submitting
    st.rerun()

if __name__ == "__main__":
    main()

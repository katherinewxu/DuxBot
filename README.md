**Women's Wellness Chatbot**

This repository contains the source code for a chatbot focused on women's wellness. The chatbot utilizes the OpenAI GPT models via LangChain and integrates a search feature using the Brave Search API to provide relevant information on various aspects of women's health and wellness.
Features

Conversational AI powered by OpenAI's GPT models
Integration with Brave Search API for up-to-date information
Streamlit-based user interface for easy interaction
Focus on women's health and wellness topics

Project Setup
Prerequisites

Python 3.7 or newer
Poetry for dependency management

Environment Setup

Clone the Repository
Start by cloning the repository to your local machine:
```git clone https://github.com/your-username/womens-wellness-chatbot.git
cd womens-wellness-chatbot```

Install Dependencies
Use Poetry to install the project dependencies. This will create a virtual environment and install all required packages as specified in pyproject.toml and poetry.lock:
```poetry install```

Setup Environment Variables
The application requires API keys from OpenAI and the Brave Search API. Create a .env file in the root of your project directory and add your API keys:
```OPENAI_API_KEY=your_openai_api_key_here
BRAVE_SEARCH_API_KEY=your_brave_search_api_key_here```
Make sure the ```.env``` file is located correctly relative to your application's expected path for loading environment variables.

Running the Application
To run the application, use the following command from the root of the project directory:
```poetry run streamlit run womens_wellness_chatbot/chatbot.py```
This will start the Streamlit server and open the chatbot interface in your default web browser. Once the application is running, you can interact with the chatbot by typing your questions or concerns related to women's wellness. 

import os
import google.auth
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google import genai
from google.genai import types

def generate():
    # Path to your OAuth 2.0 credentials file (downloaded JSON file)
    credentials_file = "A:\final year project\AyuCare\credentials.json"
    
    # Define the required scopes
    SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]

    # Check if we have existing credentials
    credentials = None
    if os.path.exists('token.json'):
        credentials = google.auth.load_credentials_from_file('token.json')[0]
    
    # If there are no valid credentials, prompt the user to log in
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            credentials = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(credentials.to_json())

    # Use the credentials to authenticate the GenAI client
    client = genai.Client(
        vertexai=True,
        project="ayucare-demo",
        location="us-central1",
        credentials=credentials  # Pass OAuth credentials here
    )

    model = "gemini-2.5-pro-preview-05-06"
    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text="""how is my bmi index if my weight is 64kg and height is 172 cm""")]
        ),
    ]

    generate_content_config = types.GenerateContentConfig(
        temperature=1,
        top_p=0.95,
        seed=0,
        max_output_tokens=8192,
        response_modalities=["TEXT"],
        safety_settings=[
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF")
        ],
    )

    # Streaming output
    for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
    ):
        print(chunk.text, end="")

# Call the function
generate()

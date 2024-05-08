import azure.functions as func
import datetime
import json
import logging
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import os

def GmailAuth(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing Gmail OAuth request.')

    # Environment variables
    kv_url = os.environ["KEYVAULT_URL"]
    client = SecretClient(vault_url=kv_url, credential=DefaultAzureCredential())

    # Load client ID and secret from Key Vault
    client_id = client.get_secret("GmailClientId").value
    client_secret = client.get_secret("GmailClientSecret").value

   # Setup the Google OAuth Flow
    flow = Flow.from_client_config(
        client_config={
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["https://email-copilot-prototype-app.azurewebsites.net/api/GmailAuth"],
            }
        },
        scopes=['https://www.googleapis.com/auth/gmail.readonly'],
        redirect_uri="https://email-copilot-prototype-app.azurewebsites.net/api/GmailAuth"
    )

    # Check if this is the callback request with auth code
    code = req.params.get('code')
    if code:
        flow.fetch_token(code=code)
        credentials = flow.credentials
        # Store the credentials securely in Key Vault
        client.set_secret("GmailToken", credentials.token)
        client.set_secret("GmailRefreshToken", credentials.refresh_token)

        return func.HttpResponse("Authentication successful", status_code=200)
    else:
        # Generate the authorization URL for the OAuth flow
        auth_url, _ = flow.authorization_url(prompt='consent')
        return func.HttpResponse(f"Redirect to: {auth_url}", status_code=302)

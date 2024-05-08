!#/bin/bash

export RG_NAME=rg-tonttu-ai-email-copilot-prototype
export LOCATION=switzerlandnorth
export STORAGE_ACCOUNT_NAME=emailcopilotstorage
export FUNCTIONAPP_NAME=email-copilot-prototype-app
export AI_NAME=tonttu-ai-insights
export KV_NAME=tonttu-ai-keyvault

export FUNCTION_APP_NAME=$FUNCTIONAPP_NAME
export RESOURCE_GROUP=$RG_NAME
export KEYVAULT_NAME=$KV_NAME

# Create a resource group
az group create --name $RG_NAME --location $LOCATION

# Create a storage account
az storage account create --name $STORAGE_ACCOUNT_NAME --location $LOCATION --resource-group $RG_NAME --sku Standard_LRS

# Create a function app
az functionapp create --resource-group $RG_NAME --consumption-plan-location $LOCATION --runtime python --runtime-version 3.11 --functions-version 4 --name $FUNCTIONAPP_NAME --storage-account $STORAGE_ACCOUNT_NAME --os-type Linux

# Enable system-assigned managed identity on the function app
az functionapp identity assign --name $FUNCTIONAPP_NAME --resource-group $RG_NAME

# Create an Application Insights resource
az monitor app-insights component create --app $AI_NAME --location $LOCATION --resource-group $RG_NAME --kind web

# Connect the function app to the Application Insights resource
az monitor app-insights component connect-function --app $AI_NAME --resource-group $RG_NAME --function $FUNCTIONAPP_NAME

# Create a Key Vault
az keyvault create --name $KV_NAME --resource-group $RG_NAME --location $LOCATION

# Retrieve the principal ID of the function app
export FUNCTION_APP_PRINCIPAL_ID=$(az functionapp identity show --name $FUNCTIONAPP_NAME --resource-group $RG_NAME --query principalId --output tsv)
echo $FUNCTION_APP_PRINCIPAL_ID

# Set the function app's principal ID as a Key Vault access policy
az keyvault set-policy --name $KV_NAME --object-id $FUNCTION_APP_PRINCIPAL_ID --secret-permissions get list

# Set the Key Vault URL as an app setting in the function app
az keyvault show --name $KV_NAME --query properties.vaultUri --output tsv
export KEYVAULT_URL=$(az keyvault show --name $KV_NAME --query properties.vaultUri --output tsv)
echo $KEYVAULT_URL
export KEYVAULT_URI=$KEYVAULT_URL

az functionapp config appsettings set --name $FUNCTIONAPP_NAME --resource-group $RG_NAME --settings KEYVAULT_URL=$KEYVAULT_URL

# Store GmailClientID
az keyvault secret set --vault-name $KV_NAME --name "GmailClientId" --value 

# Store GmailClientSecret
az keyvault secret set --vault-name $KV_NAME --name "GmailClientSecret" --value 

# List secrets in the Key Vault
az keyvault secret list --vault-name $KV_NAME

# Retrieve a specific secret
az keyvault secret show --vault-name $KV_NAME --name "GmailClientId"
az keyvault secret show --vault-name $KV_NAME --name "GmailClientSecret"

# Set the Key Vault URL as an app setting in the function app
az functionapp config appsettings set --name $FUNCTION_APP_NAME --resource-group $RESOURCE_GROUP --settings KEYVAULT_URL=$KEYVAULT_URI

az functionapp config appsettings list --name $FUNCTION_APP_NAME --resource-group $RESOURCE_GROUP

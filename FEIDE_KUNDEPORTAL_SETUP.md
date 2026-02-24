# Configuring the service and data source in Feide Kundeportal

This is a checklist for configuring services and a data source in "Feide Kundeportal" (the Feide customer portal). Note that the steps below are for running the example code in this repository only, and should not be used for other services or data sources. This is for test purposes only, and is not a guideline suitable for a production-grade service.

Note: When using Feide Kundeportal, choose English to match the terms used in this guide.

Prerequisite: Get a service provider account in Feide Kundeportal.

## 0) Create a new Feide service

- Go to **Services** and choose **Create a new service**.
- In the wizard, enter a recognizable name, and select **For internal use only** under "Who will use the service?".
- Complete registration by writing a description, choosing **No, the service does not support Single Logout**, and saving.
- After this, go to the tab **User information**.
- Check the relevant attribute groups (for tests you can choose all, and enter test-appropriate justifications where required).
- Save before moving to **Configurations**.

## 1) Configure the OIDC client for the Feide service

- Open the **Configurations** tab and choose **Add OIDC-configuration**.
- Set **Redirect URI after login** to your local callback URL, e.g. `http://localhost:8000/callback`.
- Set **Redirect URI for logout** to your post-logout URL, e.g. `http://localhost:8000/post-logout`.
- Enable **Allow login with service provider users and Feide's test users in the service provider organization**.
  This will allow you to log in with these test users: `https://docs.feide.no/reference/testusers.html`.

- Save and then take note of the **client id**.
- Click **Generate client secret** and take note of the generated value.

Update `.env` for the client examples:
- `OIDC_CLIENT_ID` = the client id from the OIDC configuration.
- `OIDC_CLIENT_SECRET` = the client secret from the OIDC configuration.
- `OIDC_REDIRECT_URI` = the redirect URI you registered (e.g. `http://localhost:8000/callback`).
- `POST_LOGOUT_REDIRECT_URI` = the logout redirect URI you registered (e.g. `http://localhost:8000/post-logout`).
- `FEIDE_ISSUER` = keep default unless you were given a different issuer.

## 2) Create the data source (API)

- Choose **Data sources** in the menu and click **Create data source**.
- Fill in required data in the wizard (description and documentation URL).
- In the tab **Technical**:
    - For **API endpoint**, enter the base URL for your data source API (HTTPS, no trailing slash).
    - For **Link to Documentation**, use a test URL (this is shown to consumers).
    - Take note of **Client ID** (for environment variable `DATASOURCE_CLIENT_ID`).
    - Generate a client secret and take note of it (for environment variable `DATASOURCE_CLIENT_SECRET`).
    - Click **Continue**.
- In the tab **Access**
    - Add at least one access level. The access level identifier becomes the scope, e.g. `read_user_info` as the value for name and identifier
    - Choose if you want to manually approve request for access, see **Connect the service to the data source** below
    - Click **Add** and **Continue**
- In the tab **User information**
    - Check all user attributes the data source should read from the Feide APIs. Also check **Organizational affiliations** and **Group entitlements for education**.
    - Click **Continue**
- Click **Continue** in the **Logo** tab
- In the tab **Visibility**, choose **Internal**. The data source with only be visible for services created by you - including the one you just configured. .**Public* will make it visible to all organizations.
- Click **Create data source**

Update `.env` for the data source example:
- `DATASOURCE_CLIENT_ID` / `DATASOURCE_CLIENT_SECRET` = credentials for the data source.
- `DATASOURCE_AUDIENCE` = `https://n.feide.no/datasources/<UUID>` for the data source.
- `DATASOURCE_REQUIRED_SCOPE` = access level identifier you created (e.g. `read_user_info`).

## 3) Connect the service to the data source

- In the service you created in the first step, open the **Data source** tab and request access to the data source and access level.
- If approval is required, approve it.


Update `.env` (client examples using token exchange):
- `FEIDE_TOKEN_EXCHANGE_AUDIENCE` = the data source audience (`https://n.feide.no/datasources/<UUID>`).
- `FEIDE_TOKEN_EXCHANGE_SCOPE` = set to the data source scope, e.g. "read_user_info"

Update `.env` (used when data source calls Feide APIs):
- `DATASOURCE_TOKEN_EXCHANGE_AUDIENCE` = usually `https://auth.dataporten.no`.
- `DATASOURCE_TOKEN_EXCHANGE_SCOPE` = Feide API scopes enabled for the data source (can be empty to request all allowed).

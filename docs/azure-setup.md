# Azure Entra ID Setup Guide

This guide walks you through setting up Microsoft Entra ID (Azure AD) for the F-Prime MCP Server.

## Prerequisites

- Azure subscription with Entra ID (Azure AD)
- Global Administrator or Application Administrator role
- Access to create security groups

## Step 1: Register the Application

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Microsoft Entra ID** → **App registrations**
3. Click **New registration**
4. Configure:
   - **Name**: `F-Prime MCP Server`
   - **Supported account types**: `Accounts in this organizational directory only`
   - **Redirect URI**: 
     - Platform: `Web`
     - URI: `http://localhost:8000/auth/callback` (add production URL later)
5. Click **Register**

## Step 2: Note Important IDs

After registration, note these values from the **Overview** page:

- **Application (client) ID**: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
- **Directory (tenant) ID**: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

## Step 3: Create Client Secret

1. Go to **Certificates & secrets**
2. Click **New client secret**
3. Add description: `MCP Server Secret`
4. Select expiration (recommended: 24 months)
5. Click **Add**
6. **Copy the secret value immediately** (you won't see it again)

## Step 4: Configure API Permissions

1. Go to **API permissions**
2. Click **Add a permission**
3. Select **Microsoft Graph** → **Delegated permissions**
4. Add these permissions:
   - `openid`
   - `profile`
   - `email`
   - `User.Read`
   - `GroupMember.Read.All` (for group membership)
5. Click **Grant admin consent** for your organization

## Step 5: Expose an API (for custom scopes)

1. Go to **Expose an API**
2. Click **Set** next to Application ID URI
3. Accept the default or set custom: `api://fprime-mcp-server`
4. Click **Add a scope**:
   - **Scope name**: `access`
   - **Who can consent**: `Admins and users`
   - **Admin consent display name**: `Access F-Prime MCP Server`
   - **Admin consent description**: `Allows access to F-Prime MCP Server tools`
   - **State**: `Enabled`

## Step 6: Configure Token Claims

To include group memberships in tokens:

1. Go to **Token configuration**
2. Click **Add groups claim**
3. Select:
   - **Security groups**
   - For ID token: Check `Group ID`
   - For Access token: Check `Group ID`
4. Click **Add**

### Optional: Add App Roles

Instead of (or in addition to) groups, you can use app roles:

1. Go to **App roles**
2. Click **Create app role**:
   - **Display name**: `F-Prime Member`
   - **Allowed member types**: `Users/Groups`
   - **Value**: `FPrime.Member`
   - **Description**: `Standard F-Prime team member`
3. Create another for admins:
   - **Display name**: `F-Prime Admin`
   - **Value**: `FPrime.Admin`
   - **Description**: `F-Prime administrator`

## Step 7: Create F-Prime Security Group

1. Go to **Microsoft Entra ID** → **Groups**
2. Click **New group**
3. Configure:
   - **Group type**: `Security`
   - **Group name**: `F-Prime Members`
   - **Group description**: `Members with access to F-Prime MCP Server`
   - **Membership type**: `Assigned`
4. Click **Create**
5. **Note the Group Object ID** from the group's overview page

## Step 8: Add Members to Group

1. Open the `F-Prime Members` group
2. Go to **Members** → **Add members**
3. Add users who should have access

## Step 9: Assign App Roles (if using roles)

1. Go to **Enterprise applications**
2. Find and select `F-Prime MCP Server`
3. Go to **Users and groups** → **Add user/group**
4. Select users/groups and assign the appropriate role

## Step 10: Configure the MCP Server

Update your `.env` file with the values from Azure:

```bash
# Microsoft Entra ID Configuration
AZURE_TENANT_ID=your-tenant-id-here
AZURE_CLIENT_ID=your-client-id-here
AZURE_CLIENT_SECRET=your-client-secret-here

# F-Prime Authorization
FPRIME_GROUP_ID=your-fprime-group-object-id-here

# If using app roles instead of/in addition to groups
# FPRIME_APP_ROLE=FPrime.Member
```

## Production Considerations

### Add Production Redirect URIs

1. Go to **Authentication**
2. Add your production callback URL:
   - `https://your-production-domain.com/auth/callback`

### Enable HTTPS

Ensure your production server uses HTTPS. Azure AD requires HTTPS for redirect URIs (except localhost).

### Token Lifetime

Default token lifetimes:
- Access tokens: 1 hour
- Refresh tokens: 90 days (with activity)

To customize, use Conditional Access policies or Token Lifetime policies.

### Conditional Access (Optional)

For additional security, create Conditional Access policies:

1. Go to **Security** → **Conditional Access**
2. Create policy requiring:
   - MFA for F-Prime MCP Server access
   - Compliant device
   - Specific locations

## Troubleshooting

### "AADSTS50011: Reply URL mismatch"

- Verify redirect URI matches exactly (including trailing slash)
- Check for http vs https mismatch

### "AADSTS65001: User consent required"

- Admin needs to grant consent for the application
- Go to API permissions and click "Grant admin consent"

### "Groups claim is empty"

- Verify groups claim is configured in Token configuration
- User might be in more than 200 groups (use roles instead)
- Check that the security group type is "Security", not "Microsoft 365"

### "Access denied" for F-Prime member

- Verify user is in the F-Prime Members security group
- Check that FPRIME_GROUP_ID matches the group's Object ID
- If using roles, verify role assignment in Enterprise Applications

## Security Best Practices

1. **Rotate secrets regularly** - Set calendar reminders before expiration
2. **Use managed identities** in production where possible
3. **Monitor sign-ins** via Entra ID sign-in logs
4. **Enable audit logging** for security events
5. **Review group memberships** periodically
6. **Use Conditional Access** for additional security controls
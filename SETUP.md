# Google Cloud Run Setup Guide

This guide walks you through setting up automated deployment to Google Cloud Run via GitHub Actions.

## Prerequisites

- Google Cloud account with billing enabled
- GitHub repository admin access
- `gcloud` CLI installed locally ([installation guide](https://cloud.google.com/sdk/docs/install))

## Step 1: Google Cloud Project Setup

### 1.1 Create or Select a Project

```bash
# List existing projects
gcloud projects list

# Create a new project (optional)
gcloud projects create YOUR-PROJECT-ID --name="fikak_app"

# Set the project as default
gcloud config set project YOUR-PROJECT-ID
```

### 1.2 Enable Required APIs

```bash
# Enable necessary Google Cloud APIs
gcloud services enable artifactregistry.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable iamcredentials.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

### 1.3 Create Artifact Registry Repository

```bash
# Create a Docker repository in Artifact Registry
gcloud artifacts repositories create fikak-app \
  --repository-format=docker \
  --location=us-central1 \
  --description="Docker repository for fikak_app"

# Verify creation
gcloud artifacts repositories list
```

## Step 2: Workload Identity Federation Setup

Workload Identity Federation allows GitHub Actions to authenticate with Google Cloud without storing long-lived service account keys.

### 2.1 Create Workload Identity Pool

```bash
# Create the identity pool
gcloud iam workload-identity-pools create "github-pool" \
  --project="YOUR-PROJECT-ID" \
  --location="global" \
  --display-name="GitHub Actions Pool"

# Get the pool ID (save this for later)
gcloud iam workload-identity-pools describe "github-pool" \
  --project="YOUR-PROJECT-ID" \
  --location="global" \
  --format="value(name)"
```

### 2.2 Create Workload Identity Provider

```bash
# Create the provider (replace YOUR-GITHUB-USERNAME/YOUR-REPO)
gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --project="YOUR-PROJECT-ID" \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --display-name="GitHub Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
  --attribute-condition="assertion.repository_owner == 'YOUR-GITHUB-USERNAME'" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# Get the full provider name (save this for later)
gcloud iam workload-identity-pools providers describe "github-provider" \
  --project="YOUR-PROJECT-ID" \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --format="value(name)"
```

The output will look like:
```
projects/123456789/locations/global/workloadIdentityPools/github-pool/providers/github-provider
```

**Save this value - you'll need it for GitHub variables!**

### 2.3 Create Service Account

```bash
# Create a service account for GitHub Actions
gcloud iam service-accounts create github-actions \
  --project="YOUR-PROJECT-ID" \
  --display-name="GitHub Actions Service Account"

# Get the service account email
gcloud iam service-accounts list --project="YOUR-PROJECT-ID"
```

### 2.4 Grant Service Account Permissions

```bash
# Set your project and service account email
PROJECT_ID="YOUR-PROJECT-ID"
SA_EMAIL="github-actions@${PROJECT_ID}.iam.gserviceaccount.com"

# Grant Artifact Registry Admin (to push Docker images)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/artifactregistry.admin"

# Grant Cloud Run Admin (to deploy services)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/run.admin"

# Grant Service Account User (to act as service account)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/iam.serviceAccountUser"

# Grant Storage Admin (for Cloud Build)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.admin"
```

### 2.5 Allow GitHub to Impersonate Service Account

```bash
# Replace YOUR-GITHUB-USERNAME and YOUR-REPO-NAME
PROJECT_ID="YOUR-PROJECT-ID"
SA_EMAIL="github-actions@${PROJECT_ID}.iam.gserviceaccount.com"
REPO="YOUR-GITHUB-USERNAME/YOUR-REPO-NAME"

gcloud iam service-accounts add-iam-policy-binding "${SA_EMAIL}" \
  --project="${PROJECT_ID}" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/PROJECT-NUMBER/locations/global/workloadIdentityPools/github-pool/attribute.repository/${REPO}"
```

**Note:** Get your PROJECT-NUMBER with:
```bash
gcloud projects describe YOUR-PROJECT-ID --format="value(projectNumber)"
```

## Step 3: GitHub Repository Configuration

### 3.1 Add Repository Variables

Go to your GitHub repository:
1. Navigate to **Settings** → **Secrets and variables** → **Actions** → **Variables** tab
2. Click **New repository variable**
3. Add the following variables:

| Variable Name | Value | Example |
|--------------|-------|---------|
| `GCP_PROJECT_ID` | Your Google Cloud project ID | `my-project-123456` |
| `GCP_REGION` | Deployment region | `us-central1` |
| `CLOUD_RUN_SERVICE` | Cloud Run service name | `fikak-app` |
| `WORKLOAD_IDENTITY_PROVIDER` | Full provider path from Step 2.2 | `projects/123.../providers/github-provider` |

### 3.2 Update Workflow File

The workflow file `.github/workflows/google-cloudrun-docker.yml` should be updated with your values OR use GitHub variables:

```yaml
env:
  PROJECT_ID: ${{ vars.GCP_PROJECT_ID }}
  REGION: ${{ vars.GCP_REGION }}
  SERVICE: ${{ vars.CLOUD_RUN_SERVICE }}
  WORKLOAD_IDENTITY_PROVIDER: ${{ vars.WORKLOAD_IDENTITY_PROVIDER }}
```

## Step 4: Test Deployment

### 4.1 Local Docker Build Test

```bash
# Build locally to test
docker build -t fikak-app .

# Run locally
docker run -p 8080:8080 fikak-app

# Test in another terminal
curl http://localhost:8080/health
```

### 4.2 Manual Cloud Run Deployment

```bash
# Authenticate Docker with Artifact Registry
gcloud auth configure-docker us-central1-docker.pkg.dev

# Build and push manually
docker build -t us-central1-docker.pkg.dev/YOUR-PROJECT-ID/fikak-app/app:v1 .
docker push us-central1-docker.pkg.dev/YOUR-PROJECT-ID/fikak-app/app:v1

# Deploy to Cloud Run
gcloud run deploy fikak-app \
  --image us-central1-docker.pkg.dev/YOUR-PROJECT-ID/fikak-app/app:v1 \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080
```

### 4.3 Automated Deployment via GitHub Actions

1. Make a change to your code
2. Commit and push to the `main` branch:
   ```bash
   git add .
   git commit -m "Test automated deployment"
   git push origin main
   ```
3. Go to **Actions** tab in GitHub to watch the deployment
4. Once complete, access your app at the Cloud Run URL

## Step 5: Verify Deployment

### 5.1 Get Cloud Run URL

```bash
gcloud run services describe fikak-app \
  --platform managed \
  --region us-central1 \
  --format 'value(status.url)'
```

### 5.2 Test Endpoints

```bash
# Set your Cloud Run URL
CLOUD_RUN_URL="https://fikak-app-xxxxx-uc.a.run.app"

# Test health endpoint
curl $CLOUD_RUN_URL/health

# Test info endpoint
curl $CLOUD_RUN_URL/api/info

# Test echo endpoint
curl -X POST $CLOUD_RUN_URL/api/echo \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

## Troubleshooting

### Issue: "Permission denied" during deployment

**Solution:** Verify service account permissions:
```bash
gcloud projects get-iam-policy YOUR-PROJECT-ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:github-actions@*"
```

### Issue: "Workload identity pool not found"

**Solution:** Ensure the Workload Identity Provider path is correct:
```bash
gcloud iam workload-identity-pools providers list \
  --workload-identity-pool="github-pool" \
  --location="global" \
  --project="YOUR-PROJECT-ID"
```

### Issue: "Docker image not found"

**Solution:** Verify Artifact Registry setup:
```bash
gcloud artifacts repositories list --project="YOUR-PROJECT-ID"
gcloud artifacts docker images list \
  us-central1-docker.pkg.dev/YOUR-PROJECT-ID/fikak-app
```

### Issue: GitHub Actions workflow fails

**Solution:** Check workflow logs in GitHub Actions tab and verify:
1. All variables are set correctly
2. Workload Identity Federation is configured properly
3. Service account has necessary permissions

## Security Best Practices

1. **Never commit service account keys** to the repository
2. **Use Workload Identity Federation** instead of long-lived keys
3. **Apply least privilege** to service accounts
4. **Enable Cloud Run IAM** for production deployments (remove `--allow-unauthenticated`)
5. **Use Secret Manager** for sensitive configuration
6. **Enable Cloud Armor** for DDoS protection
7. **Set up Cloud Monitoring** alerts

## Cost Optimization

1. **Set CPU throttling**: `--cpu-throttling` (only allocate CPU during requests)
2. **Limit instances**: `--max-instances=10`
3. **Set memory limits**: `--memory=512Mi`
4. **Configure timeout**: `--timeout=60s`
5. **Use Cloud Scheduler** to keep instances warm if needed

## Next Steps

- [ ] Set up custom domain with Cloud Run
- [ ] Configure Cloud CDN for caching
- [ ] Enable Cloud Monitoring and Logging
- [ ] Set up alerting policies
- [ ] Implement Cloud Armor for security
- [ ] Add Secret Manager for secrets
- [ ] Configure Cloud SQL if database needed
- [ ] Set up staging environment

## Additional Resources

- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Workload Identity Federation Setup](https://github.com/google-github-actions/auth#setup)
- [GitHub Actions for Google Cloud](https://github.com/google-github-actions)
- [Cloud Run Best Practices](https://cloud.google.com/run/docs/best-practices)

---

**Last Updated:** 2026-01-16

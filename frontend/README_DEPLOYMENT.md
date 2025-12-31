# Frontend Deployment Configuration

## API Configuration

The frontend now uses a dynamic API configuration that automatically detects the correct backend URL based on the deployment environment.

### How it works:

1. **Development**: When running on `localhost` or `127.0.0.1`, it uses `http://localhost:8000`
2. **Production**: When deployed to a domain, it uses the same domain for API calls
3. **Custom Backend**: You can override this by setting the `NEXT_PUBLIC_BACKEND_URL` environment variable

### Deployment Options:

#### Option 1: Backend and Frontend on the Same Domain
If your backend API is served from the same domain as your frontend (e.g., `/api/*` routes), no additional configuration is needed. The app will automatically use the current domain.

#### Option 2: Backend on a Different Domain
If your backend is deployed separately, set the `NEXT_PUBLIC_BACKEND_URL` environment variable:

```bash
# For Vercel
NEXT_PUBLIC_BACKEND_URL=https://your-backend-domain.com

# For other platforms, check their environment variable documentation
```

### Examples:

- **Local development**: `http://localhost:8000` (automatic)
- **Same domain deployment**: `https://yourdomain.com` (automatic)
- **Separate backend**: `https://api.yourdomain.com` (via environment variable)

## Building for Production

```bash
cd frontend
npm run build
npm start
```

## Environment Variables

Create a `.env.local` file in the frontend directory for local development:

```
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

For production deployment, configure the environment variable according to your hosting platform's documentation.




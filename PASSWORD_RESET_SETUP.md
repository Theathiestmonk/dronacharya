# Password Reset Functionality Setup

## Overview
This implementation adds password reset functionality to your chatbot login system using Supabase's built-in authentication features.

## Features Added

### 1. Password Reset Functions
- `resetPassword(email)` - Sends password reset email
- `updatePassword(newPassword)` - Updates user password

### 2. Components Created
- `ForgotPassword.tsx` - Form to request password reset
- `ResetPassword.tsx` - Form to set new password
- `/reset-password` page - Route for password reset

### 3. Updated Components
- `AuthForm.tsx` - Added "Forgot Password" link
- `AuthProvider.tsx` - Added reset functions to context

## How It Works

### 1. User Requests Password Reset
1. User clicks "Forgot your password?" on login form
2. User enters email address
3. System sends reset email via Supabase
4. User receives email with reset link

### 2. User Resets Password
1. User clicks link in email
2. Redirected to `/reset-password` page
3. User enters new password
4. Password is updated in Supabase
5. User is redirected to dashboard

## Supabase Configuration Required

### 1. Email Templates
In your Supabase dashboard:
1. Go to Authentication > Email Templates
2. Customize the "Reset Password" template
3. Set redirect URL to: `https://yourdomain.com/reset-password`

### 2. Site URL Configuration
1. Go to Authentication > URL Configuration
2. Add to "Redirect URLs":
   - `https://yourdomain.com/reset-password`
   - `http://localhost:3000/reset-password` (for development)

### 3. Email Settings
1. Go to Authentication > Settings
2. Configure your email provider (SMTP)
3. Or use Supabase's default email service

## Usage

### For Users
1. Go to login page
2. Click "Forgot your password?"
3. Enter email address
4. Check email for reset link
5. Click link and set new password

### For Developers
```typescript
// Reset password
const { error } = await resetPassword('user@example.com');

// Update password (when user is logged in)
const { error } = await updatePassword('newpassword123');
```

## Security Features
- ✅ Email verification required
- ✅ Secure token-based reset
- ✅ Password validation
- ✅ Automatic session management
- ✅ CSRF protection via Supabase

## Testing
1. Start your development server
2. Go to login page
3. Click "Forgot your password?"
4. Enter a valid email
5. Check email for reset link
6. Test password reset flow

## Troubleshooting

### Common Issues
1. **Email not received**: Check spam folder, verify email configuration
2. **Reset link not working**: Check redirect URL configuration
3. **Password update fails**: Ensure user is authenticated

### Debug Steps
1. Check browser console for errors
2. Verify Supabase configuration
3. Check email delivery logs in Supabase
4. Test with different email providers

## Files Modified/Created
- ✅ `frontend/src/providers/AuthProvider.tsx` - Added reset functions
- ✅ `frontend/src/components/ForgotPassword.tsx` - New component
- ✅ `frontend/src/components/ResetPassword.tsx` - New component
- ✅ `frontend/src/components/AuthForm.tsx` - Added forgot password link
- ✅ `frontend/src/app/reset-password/page.tsx` - New page

Your password reset functionality is now ready to use! 🚀

#!/usr/bin/env python3

import os
import sys
import requests
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta

# Add backend to path for imports
sys.path.append(os.path.dirname(__file__))

class TokenRefreshService:
    """Service for managing Google OAuth token refresh operations"""

    def __init__(self):
        """Initialize the token refresh service"""
        pass

    def ensure_valid_token(self, token_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Ensure the token is valid, refreshing if necessary

        Args:
            token_data: Token data from database

        Returns:
            Valid token data or None if refresh fails
        """
        try:
            # Check if token needs refresh (expires within 5 minutes)
            expires_at = token_data.get('token_expires_at')
            if not expires_at:
                print("[TokenRefresh] No expiration time found, assuming token is valid")
                return token_data

            # Parse expiration time
            if isinstance(expires_at, str):
                # Try different datetime formats
                try:
                    expires_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                except ValueError:
                    try:
                        expires_dt = datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S.%f%z')
                    except ValueError:
                        print(f"[TokenRefresh] Could not parse expiration time: {expires_at}")
                        return token_data
            else:
                expires_dt = expires_at

            # Ensure timezone awareness
            if expires_dt.tzinfo is None:
                expires_dt = expires_dt.replace(tzinfo=timezone.utc)

            now = datetime.now(timezone.utc)
            time_until_expiry = expires_dt - now

            # If token expires within 5 minutes, refresh it
            if time_until_expiry.total_seconds() < 300:  # 5 minutes
                print("[TokenRefresh] Token expires soon, refreshing...")
                return self._refresh_token(token_data)
            else:
                print(f"[TokenRefresh] Token is valid, expires in {time_until_expiry}")
                return token_data

        except Exception as e:
            print(f"[TokenRefresh] Error checking token validity: {e}")
            return token_data

    def _refresh_token(self, token_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Refresh an expired Google OAuth token

        Args:
            token_data: Current token data

        Returns:
            Updated token data or None if refresh fails
        """
        try:
            refresh_token = token_data.get('refresh_token')
            if not refresh_token:
                print("[TokenRefresh] No refresh token available")
                return None

            # Google OAuth token refresh endpoint
            token_url = "https://oauth2.googleapis.com/token"

            # Prepare the refresh request
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
                'client_id': os.getenv('GOOGLE_CLIENT_ID'),
                'client_secret': os.getenv('GOOGLE_CLIENT_SECRET')
            }

            print("[TokenRefresh] Making refresh request to Google OAuth...")

            response = requests.post(token_url, data=data, timeout=30)

            if response.status_code == 200:
                token_response = response.json()

                # Calculate new expiration time
                expires_in = token_response.get('expires_in', 3600)  # Default 1 hour
                new_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

                # Update token data
                updated_token = token_data.copy()
                updated_token['access_token'] = token_response['access_token']
                updated_token['token_expires_at'] = new_expires_at.isoformat()

                # Update in database
                self._update_token_in_db(updated_token)

                print(f"[TokenRefresh] Token refreshed successfully, expires at {new_expires_at}")
                return updated_token
            else:
                print(f"[TokenRefresh] Token refresh failed: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            print(f"[TokenRefresh] Error refreshing token: {e}")
            return None

    def _update_token_in_db(self, token_data: Dict[str, Any]) -> bool:
        """
        Update the token data in the database

        Args:
            token_data: Updated token data

        Returns:
            True if update successful, False otherwise
        """
        try:
            from supabase_config import get_supabase_client

            supabase = get_supabase_client()

            # Update the token in database
            update_data = {
                'access_token': token_data['access_token'],
                'token_expires_at': token_data['token_expires_at'],
                'updated_at': datetime.now(timezone.utc).isoformat()
            }

            result = supabase.table('gcdr').update(update_data).eq('id', token_data['id']).execute()

            if result.data:
                print("[TokenRefresh] Token updated in database successfully")
                return True
            else:
                print("[TokenRefresh] Failed to update token in database")
                return False

        except Exception as e:
            print(f"[TokenRefresh] Error updating token in database: {e}")
            return False

def refresh_expired_tokens():
    """
    Refresh all expired tokens in the database
    This function is called periodically to ensure all tokens remain valid
    """
    try:
        from supabase_config import get_supabase_client
        from datetime import datetime, timezone

        supabase = get_supabase_client()
        now = datetime.now(timezone.utc)

        print("[TokenRefresh] 🔄 Starting batch token refresh process...")

        # Get all tokens that need refresh (expired or expiring soon)
        result = supabase.table('gcdr').select('*').execute()

        if not result.data:
            print("[TokenRefresh] No tokens found in database")
            return

        refreshed_count = 0
        failed_count = 0

        for token_data in result.data:
            try:
                # Check if this token needs refresh
                token_service = TokenRefreshService()
                valid_token = token_service.ensure_valid_token(token_data)

                if valid_token:
                    refreshed_count += 1
                    print(f"[TokenRefresh] ✅ Refreshed token for user: {token_data.get('user_email', 'Unknown')}")
                else:
                    failed_count += 1
                    print(f"[TokenRefresh] ❌ Failed to refresh token for user: {token_data.get('user_email', 'Unknown')}")

            except Exception as e:
                print(f"[TokenRefresh] Error processing token for user {token_data.get('user_email', 'Unknown')}: {e}")
                failed_count += 1

        print(f"[TokenRefresh] 📊 Batch refresh completed: {refreshed_count} refreshed, {failed_count} failed")

    except Exception as e:
        print(f"[TokenRefresh] Error in batch refresh process: {e}")
        raise

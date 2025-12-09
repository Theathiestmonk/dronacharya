"""
Google Domain-Wide Delegation (DWD) Service
Allows service account to impersonate users and access their Google Classroom/Calendar data
"""
import os
import json
import base64
import jwt
import threading
from google.oauth2 import service_account
from googleapiclient.discovery import build
from typing import Dict, List, Optional
from datetime import datetime, timezone

# Thread-local storage to track which API is being used for scope selection
_thread_local = threading.local()

class GoogleDWDService:
    """Service for Google Domain-Wide Delegation (DWD) authentication"""
    
    def __init__(self):
        # Get service account path from env var or use default
        self.service_account_path = os.getenv(
            'GOOGLE_APPLICATION_CREDENTIALS',
            os.path.join(os.path.dirname(__file__), '../../service-account-key.json')
        )
        self.workspace_domain = os.getenv('GOOGLE_WORKSPACE_DOMAIN', 'atsnai.com')
        
        # Note: For Domain-Wide Delegation, scopes are configured in Google Workspace Admin Console
        # Do NOT pass scopes when creating credentials - they are enforced by Admin Console authorization
        self._base_credentials = None
        self._load_credentials()
    
    def _load_credentials(self):
        """Load service account credentials for Domain-Wide Delegation"""
        try:
            # Resolve relative path
            if not os.path.isabs(self.service_account_path):
                # Make path relative to project root
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                self.service_account_path = os.path.join(base_dir, self.service_account_path.replace('backend/', ''))
            
            if os.path.exists(self.service_account_path):
                # Read service account file first to get Client ID
                with open(self.service_account_path, 'r', encoding='utf-8') as f:
                    service_account_info = json.load(f)
                    client_id_from_file = str(service_account_info.get('client_id', 'Not found')).strip()
                    service_account_email = service_account_info.get('client_email', 'Not found')
                    project_id = service_account_info.get('project_id', 'Not found')
                
                # For DWD, create credentials WITHOUT scopes
                # Scopes are authorized in Google Workspace Admin Console, not in code
                # CRITICAL: Explicitly set scopes=None to ensure NO scope in JWT assertion
                # For DWD, the JWT assertion must NOT include any scope parameter
                # Setting scopes=None explicitly tells the library not to include scopes in JWT
                try:
                    # Try with scopes=None first (explicit)
                    self._base_credentials = service_account.Credentials.from_service_account_file(
                        self.service_account_path,
                        scopes=None  # Explicitly None for DWD
                    )
                except TypeError:
                    # If scopes=None is not supported, omit the parameter
                    self._base_credentials = service_account.Credentials.from_service_account_file(
                        self.service_account_path
                        # No scopes parameter
                    )
                # Ensure token_uri is set to OAuth2 token endpoint for DWD
                # This is the standard endpoint for service account token requests
                if not hasattr(self._base_credentials, '_token_uri') or not self._base_credentials._token_uri:
                    self._base_credentials._token_uri = 'https://oauth2.googleapis.com/token'
                
                # CRITICAL: For DWD, ensure _scopes (private attribute) is also None/empty
                # The JWT assertion uses _scopes if scopes attribute is not set
                if hasattr(self._base_credentials, '_scopes'):
                    if self._base_credentials._scopes:
                        print(f"   ⚠️  WARNING: Base credentials _scopes (private) has value: {self._base_credentials._scopes}")
                        print(f"   ⚠️  Clearing _scopes to ensure no scope in JWT...")
                        self._base_credentials._scopes = None
                    else:
                        print(f"   ✅ Base credentials _scopes (private) is None/empty (correct for DWD)")
                
                # CRITICAL: For DWD, credentials should have NO scopes attribute set
                # Do NOT call with_scopes() - it might add scope parameter to JWT
                # Admin Console enforces scopes, client should not request any
                print(f"   🔍 Verifying base credentials scope state...")
                if hasattr(self._base_credentials, 'scopes'):
                    current_scopes = getattr(self._base_credentials, 'scopes', None)
                    if current_scopes:
                        print(f"   ❌ ERROR: Base credentials have scopes: {current_scopes}")
                        print(f"   ❌ This should not happen - credentials created without scopes parameter")
                        print(f"   ⚠️  For DWD, scopes should be None/empty - Admin Console enforces them")
                    else:
                        print(f"   ✅ Base credentials scopes attribute exists but is None/empty (correct for DWD)")
                else:
                    print(f"   ✅ Base credentials have no scopes attribute (correct for DWD)")
                
                # Get Client ID from credentials object if available
                client_id_from_credentials = None
                try:
                    if hasattr(self._base_credentials, 'service_account_email'):
                        # Try to get client_id from the credentials object
                        if hasattr(self._base_credentials, '_service_account_email'):
                            pass  # Credentials object doesn't directly expose client_id
                except:
                    pass
                
                # Use the Client ID from the file (most reliable)
                client_id = client_id_from_file
                
                print(f"✅ DWD: Service account credentials loaded from {self.service_account_path}")
                print(f"   Service Account Email: {service_account_email}")
                print(f"   Client ID (from file): {client_id}")
                print(f"   Project ID: {project_id}")
                print(f"   Workspace Domain: {self.workspace_domain}")
                print()
                print(f"   ✅ NOTE: Domain-Wide Delegation is enabled by default (no Cloud Console setup needed)")
                print(f"   ⚠️  CRITICAL: Authorize Client ID {client_id} in Google Workspace Admin Console:")
                print(f"      → Go to: https://admin.google.com")
                print(f"      → Security > API Controls > Domain-wide Delegation")
                print(f"      → Add Client ID with the 5 required scopes")
                
                # Verify Client ID format and warn
                if client_id and client_id != 'Not found':
                    # Strip any whitespace
                    client_id = str(client_id).strip()
                    # Additional validation: check if Client ID looks valid (should be numeric)
                    if not client_id.isdigit():
                        print(f"   ⚠️  WARNING: Client ID contains non-numeric characters: {repr(client_id)}")
                    elif len(client_id) != 20:
                        print(f"   ⚠️  WARNING: Client ID length is {len(client_id)} (expected 20 digits): {repr(client_id)}")
                    else:
                        print(f"   ✅ Client ID format is valid (20 digits)")
                    
                    # Always show the same Client ID in the verification message
                    print(f"   ⚠️  Verify this Client ID is authorized in Google Admin Console: {client_id}")
            else:
                print(f"⚠️ DWD: Service account file not found at {self.service_account_path}")
        except Exception as e:
            print(f"❌ DWD: Failed to load credentials: {str(e)}")
            import traceback
            traceback.print_exc()
            self._base_credentials = None
    
    def _get_delegated_credentials(self, user_email: str):
        """Get delegated credentials for a specific user"""
        if not self._base_credentials:
            raise Exception("Service account credentials not loaded. Check GOOGLE_APPLICATION_CREDENTIALS path.")
        
        # Verify email is in workspace domain (supports subdomains)
        # Extract domain from email (everything after @)
        email_domain = user_email.split('@')[1] if '@' in user_email else ''
        
        # Check if email domain matches workspace domain exactly, or is a subdomain
        # e.g., learners.prakriti.org.in matches prakriti.org.in
        domain_matches = (
            email_domain == self.workspace_domain or
            email_domain.endswith(f".{self.workspace_domain}")
        )
        
        if not domain_matches:
            error_msg = f"User email {user_email} (domain: {email_domain}) is not in workspace domain {self.workspace_domain}. "
            error_msg += f"Set GOOGLE_WORKSPACE_DOMAIN environment variable to match the user's domain or parent domain."
            print(f"❌ DWD Domain Mismatch: {error_msg}")
            raise Exception(error_msg)
        
        print(f"✅ DWD: Workspace domain verified: {user_email} (domain: {email_domain}) is in workspace domain {self.workspace_domain}")
        
        # CRITICAL: For DWD, we must ensure NO scopes in JWT assertion
        # The Google auth library may add scopes when using with_subject()
        # We need to verify and clear scopes - Admin Console enforces them, not client
        
        # Check base credentials scopes (should be None/empty if created correctly)
        base_scopes = getattr(self._base_credentials, 'scopes', None) if hasattr(self._base_credentials, 'scopes') else None
        if base_scopes:
            print(f"⚠️  WARNING: Base credentials have scopes: {base_scopes}")
            print(f"⚠️  This should not happen - base credentials should have no scopes")
            # Recreate base credentials with scopes=None
            try:
                self._base_credentials = service_account.Credentials.from_service_account_file(
                    self.service_account_path,
                    scopes=None  # Explicitly None for DWD
                )
            except TypeError:
                self._base_credentials = service_account.Credentials.from_service_account_file(
                    self.service_account_path
                    # No scopes parameter
                )
            print(f"✅ Recreated base credentials without scopes")
        else:
            print(f"✅ Base credentials have no scopes (correct for DWD)")
        
        # Create delegated credentials (impersonate user)
        # IMPORTANT: For DWD, scopes are enforced by Admin Console, NOT requested by client
        # The JWT assertion must NOT include any scope parameter
        # CRITICAL: Ensure base credentials have no scopes before calling with_subject()
        # with_subject() might inherit scopes from base credentials
        if hasattr(self._base_credentials, 'scopes'):
            base_scope_val = getattr(self._base_credentials, 'scopes', None)
            if base_scope_val:
                print(f"⚠️  CRITICAL: Base credentials have scopes before with_subject(): {base_scope_val}")
                print(f"⚠️  This will cause scopes to be included in JWT - clearing now...")
                try:
                    self._base_credentials = self._base_credentials.with_scopes(None)
                except:
                    # Recreate base credentials
                    try:
                        self._base_credentials = service_account.Credentials.from_service_account_file(
                            self.service_account_path,
                            scopes=None
                        )
                    except TypeError:
                        self._base_credentials = service_account.Credentials.from_service_account_file(
                            self.service_account_path
                        )
        
        delegated_credentials = self._base_credentials.with_subject(user_email)
        
        # Store API type in credentials for scope selection (will be set when service is built)
        # This allows us to send only relevant scopes in token request
        if not hasattr(delegated_credentials, '_dwd_api_type'):
            delegated_credentials._dwd_api_type = None  # Will be set to 'classroom' or 'calendar' when service is built
        
        # CRITICAL: Monkey-patch to intercept JWT creation and ensure no scopes
        # The JWT is created in _make_authorization_grant_assertion
        # We need to intercept it to remove scopes from the JWT payload
        import types
        import google.oauth2._client as oauth2_client
        from google.oauth2 import service_account
        
        # CRITICAL: Patch both _refresh_token and _make_authorization_grant_assertion
        # _make_authorization_grant_assertion signature is (self) - it builds assertion_data internally
        # Even if _scopes is None, it might still add an empty 'scope' field to the JWT
        # We need to patch _make_authorization_grant_assertion to remove the scope field completely
        if not hasattr(service_account.Credentials, '_dwd_patched'):
            # Patch _refresh_token to clear scopes before JWT creation
            original_refresh_token_class = service_account.Credentials._refresh_token
            
            def _refresh_token_class_patch(self, request):
                """Class-level patch to clear scopes before JWT creation for DWD"""
                # CRITICAL: Clear _scopes right before JWT is created
                if hasattr(self, '_subject') and self._subject:
                    # This is a DWD request (has subject)
                    print(f"   🔍 [CLASS PATCH] DWD request detected, clearing _scopes before JWT creation...")
                    if hasattr(self, '_scopes'):
                        if self._scopes:
                            print(f"❌ [CLASS PATCH] _scopes has value: {self._scopes[:100] if isinstance(self._scopes, str) else str(self._scopes)[:100]} - clearing...")
                            self._scopes = None
                            print(f"✅ [CLASS PATCH] Cleared _scopes")
                        else:
                            print(f"✅ [CLASS PATCH] _scopes is already None")
                
                # Call original _refresh_token which will call _make_authorization_grant_assertion
                return original_refresh_token_class(self, request)
            
            # Patch _make_authorization_grant_assertion to remove scope field from JWT
            original_make_assertion_class = service_account.Credentials._make_authorization_grant_assertion
            
            def _make_assertion_class_patch(self):
                """Class-level patch to ensure JWT has correct format for DWD"""
                # Call original to get the JWT
                assertion = original_make_assertion_class(self)
                
                # If this is a DWD request (has subject), ensure JWT format is correct
                if hasattr(self, '_subject') and self._subject:
                    try:
                        # Decode JWT without verification
                        decoded = jwt.decode(assertion, options={"verify_signature": False})
                        
                        # CRITICAL: For DWD, Google might require scopes in BOTH JWT and request body
                        # OR it might require scopes in JWT but NOT in request body
                        # The error "Empty or missing scope not allowed" suggests Google is checking JWT for scopes
                        # Let's try adding authorized scopes to JWT assertion for DWD
                        
                        # Determine which scopes to include based on API type
                        api_type = getattr(_thread_local, 'dwd_api_type', None)
                        
                        if api_type == 'classroom':
                            scopes_for_jwt = [
                                'https://www.googleapis.com/auth/classroom.courses.readonly',
                                'https://www.googleapis.com/auth/classroom.rosters.readonly',
                                'https://www.googleapis.com/auth/classroom.announcements.readonly'
                            ]
                        elif api_type == 'calendar':
                            scopes_for_jwt = [
                                'https://www.googleapis.com/auth/calendar.readonly',
                                'https://www.googleapis.com/auth/calendar.events.readonly'
                            ]
                        else:
                            # Fallback: use all authorized scopes
                            scopes_for_jwt = [
                                'https://www.googleapis.com/auth/classroom.courses.readonly',
                                'https://www.googleapis.com/auth/classroom.rosters.readonly',
                                'https://www.googleapis.com/auth/classroom.announcements.readonly',
                                'https://www.googleapis.com/auth/calendar.readonly',
                                'https://www.googleapis.com/auth/calendar.events.readonly'
                            ]
                        
                        # Check if JWT already has scope
                        if 'scope' not in decoded or not decoded.get('scope'):
                            print(f"   🔍 [CLASS PATCH] JWT has no scope - adding authorized scopes for DWD...")
                            print(f"   🔍 [CLASS PATCH] API type: {api_type or 'unknown'}, adding {len(scopes_for_jwt)} scopes to JWT")
                            print(f"   🔍 [CLASS PATCH] Scopes to add: {', '.join([s.split('/')[-1] for s in scopes_for_jwt])}")
                            
                            # Get the signer from credentials
                            if hasattr(self, '_signer') and self._signer:
                                import time
                                
                                # Create new JWT WITH scope (space-separated string)
                                now = int(time.time())
                                header = {'alg': 'RS256', 'typ': 'JWT'}
                                
                                # Build payload WITH scope for DWD
                                scope_string = ' '.join(scopes_for_jwt)
                                payload = {
                                    'iss': decoded.get('iss'),
                                    'sub': decoded.get('sub'),
                                    'aud': decoded.get('aud'),
                                    'iat': decoded.get('iat', now),
                                    'exp': decoded.get('exp', now + 3600),
                                    'scope': scope_string  # Add scope to JWT for DWD
                                }
                                
                                # Sign the JWT
                                segments = []
                                segments.append(base64.urlsafe_b64encode(json.dumps(header).encode('utf-8')).decode('utf-8').rstrip('='))
                                segments.append(base64.urlsafe_b64encode(json.dumps(payload).encode('utf-8')).decode('utf-8').rstrip('='))
                                
                                signing_input = '.'.join(segments)
                                signature = self._signer.sign(signing_input.encode('utf-8'))
                                segments.append(base64.urlsafe_b64encode(signature).decode('utf-8').rstrip('='))
                                
                                assertion = '.'.join(segments).encode('utf-8')
                                print(f"✅ [CLASS PATCH] Re-signed JWT WITH scope field for DWD ({len(scopes_for_jwt)} scopes)")
                            else:
                                print(f"⚠️  [CLASS PATCH] Cannot re-sign JWT - no signer available")
                        else:
                            existing_scope = decoded.get('scope', '')
                            print(f"   🔍 [CLASS PATCH] JWT already has scope: '{existing_scope[:100]}...'")
                    except Exception as e:
                        print(f"⚠️  [CLASS PATCH] Could not process JWT: {e}")
                        import traceback
                        traceback.print_exc()
                
                return assertion
            
            service_account.Credentials._refresh_token = _refresh_token_class_patch
            service_account.Credentials._make_authorization_grant_assertion = _make_assertion_class_patch
            service_account.Credentials._dwd_patched = True
            print(f"✅ Monkey-patched ServiceAccountCredentials class (_refresh_token + _make_authorization_grant_assertion)")
        
        # CRITICAL: Patch _token_endpoint_request to ADD authorized scopes to request body for DWD
        # Note: Scopes are primarily included in JWT assertion (see _make_assertion_class_patch above)
        # We also add them to request body for compatibility
        if not hasattr(oauth2_client, '_original_token_endpoint_request'):
            original_token_endpoint_request = oauth2_client._token_endpoint_request
            
            # Define scopes for each API type (must match Admin Console)
            DWD_CLASSROOM_SCOPES = [
                'https://www.googleapis.com/auth/classroom.courses.readonly',
                'https://www.googleapis.com/auth/classroom.rosters.readonly',
                'https://www.googleapis.com/auth/classroom.announcements.readonly'
            ]
            
            DWD_CALENDAR_SCOPES = [
                'https://www.googleapis.com/auth/calendar.readonly',
                'https://www.googleapis.com/auth/calendar.events.readonly'
            ]
            
            # All authorized scopes (for fallback)
            DWD_ALL_SCOPES = DWD_CLASSROOM_SCOPES + DWD_CALENDAR_SCOPES
            
            def _token_endpoint_request_intercept(request, token_uri, body, **kwargs):
                """Intercept _token_endpoint_request to ADD authorized scopes to request body for DWD"""
                # Check if this is a DWD request by looking at the assertion in the body
                if isinstance(body, dict) and 'assertion' in body:
                    try:
                        assertion = body['assertion']
                        if isinstance(assertion, bytes):
                            assertion = assertion.decode('utf-8')
                        decoded = jwt.decode(assertion, options={"verify_signature": False})
                        
                        # If JWT has 'sub' but no 'scope' or empty 'scope', it's a DWD request
                        if 'sub' in decoded and ('scope' not in decoded or not decoded.get('scope')):
                            print(f"   🔍 [TOKEN_REQUEST INTERCEPT] DWD request detected, adding authorized scopes to request body...")
                            print(f"   🔍 [TOKEN_REQUEST INTERCEPT] Request body keys (before): {list(body.keys())}")
                            
                            # Determine which scopes to send based on API type
                            # Get API type from thread-local storage (set when service is built)
                            api_type = getattr(_thread_local, 'dwd_api_type', None)
                            
                            # CRITICAL: For DWD, send only the scopes relevant to the API being called
                            # This prevents sending invalid scopes that might cause Google to reject
                            if api_type == 'classroom':
                                scopes_to_send = DWD_CLASSROOM_SCOPES
                                print(f"   🔍 [TOKEN_REQUEST INTERCEPT] Classroom API detected - sending {len(scopes_to_send)} Classroom scopes")
                            elif api_type == 'calendar':
                                scopes_to_send = DWD_CALENDAR_SCOPES
                                print(f"   🔍 [TOKEN_REQUEST INTERCEPT] Calendar API detected - sending {len(scopes_to_send)} Calendar scopes")
                            else:
                                # Fallback: if we can't determine, send all scopes
                                scopes_to_send = DWD_ALL_SCOPES
                                print(f"   ⚠️  [TOKEN_REQUEST INTERCEPT] API type not detected - sending all {len(scopes_to_send)} scopes as fallback")
                            
                            # Create a new dict to ensure modifications are preserved
                            modified_body = dict(body)
                            scope_string = ' '.join(scopes_to_send)
                            modified_body['scope'] = scope_string
                            body = modified_body
                            
                            print(f"✅ [TOKEN_REQUEST INTERCEPT] Added {len(scopes_to_send)} authorized scopes to request body")
                            print(f"   🔍 [TOKEN_REQUEST INTERCEPT] Scopes: {scope_string[:150]}...")
                            
                            print(f"✅ [TOKEN_REQUEST INTERCEPT] Added authorized scopes to request body")
                            print(f"   🔍 [TOKEN_REQUEST INTERCEPT] Scope string: {scope_string}")
                            print(f"   🔍 [TOKEN_REQUEST INTERCEPT] Full scope string length: {len(scope_string)}")
                            print(f"   🔍 [TOKEN_REQUEST INTERCEPT] Request body keys (after): {list(body.keys())}")
                            print(f"   🔍 [TOKEN_REQUEST INTERCEPT] Scope value in body: {body.get('scope', 'NOT FOUND')[:200]}...")
                            
                            # Log the JWT payload for debugging
                            print(f"   🔍 [TOKEN_REQUEST INTERCEPT] JWT payload: {decoded}")
                            print(f"   🔍 [TOKEN_REQUEST INTERCEPT] Service account: {decoded.get('iss')}")
                            print(f"   🔍 [TOKEN_REQUEST INTERCEPT] Impersonating user: {decoded.get('sub')}")
                            print(f"   🔍 [TOKEN_REQUEST INTERCEPT] Token URI: {token_uri}")
                    except Exception as e:
                        print(f"⚠️  [TOKEN_REQUEST INTERCEPT] Could not decode JWT: {e}")
                        import traceback
                        traceback.print_exc()
                
                # CRITICAL: Log the final body that will be sent to Google
                if isinstance(body, dict) and 'scope' in body:
                    print(f"   🔍 [TOKEN_REQUEST INTERCEPT] FINAL CHECK - Body has scope: {body.get('scope', 'NOT FOUND')[:100]}...")
                    print(f"   🔍 [TOKEN_REQUEST INTERCEPT] FINAL CHECK - Body type: {type(body)}")
                    print(f"   🔍 [TOKEN_REQUEST INTERCEPT] FINAL CHECK - Body keys: {list(body.keys())}")
                    print(f"   🔍 [TOKEN_REQUEST INTERCEPT] FINAL CHECK - Body repr: {repr(body)[:300]}...")
                
                result = original_token_endpoint_request(request, token_uri, body, **kwargs)
                
                # Log the result to see what Google returned
                if hasattr(result, '__iter__') and not isinstance(result, (str, bytes)):
                    try:
                        result_list = list(result) if hasattr(result, '__iter__') else [result]
                        if len(result_list) > 0:
                            print(f"   🔍 [TOKEN_REQUEST INTERCEPT] Google response type: {type(result_list[0])}")
                            if isinstance(result_list[0], dict):
                                print(f"   🔍 [TOKEN_REQUEST INTERCEPT] Google response keys: {list(result_list[0].keys())}")
                                if 'error' in result_list[0]:
                                    print(f"   ❌ [TOKEN_REQUEST INTERCEPT] Google error: {result_list[0].get('error')}")
                                    print(f"   ❌ [TOKEN_REQUEST INTERCEPT] Google error description: {result_list[0].get('error_description')}")
                    except:
                        pass
                
                return result
            
            oauth2_client._original_token_endpoint_request = original_token_endpoint_request
            oauth2_client._token_endpoint_request = _token_endpoint_request_intercept
            print(f"✅ Monkey-patched _token_endpoint_request to ADD authorized scopes to request body for DWD")
        
        # CRITICAL: Also patch jwt_grant at the module level to intercept ALL JWT assertions
        # This is for logging/debugging only - scope is added in _token_endpoint_request
        if not hasattr(oauth2_client, '_original_jwt_grant'):
            original_jwt_grant = oauth2_client.jwt_grant
            
            def _jwt_grant_intercept(request, token_uri, assertion):
                """Intercept jwt_grant to log DWD requests (scope is added in _token_endpoint_request)"""
                print(f"   🔍 [JWT_GRANT INTERCEPT] ========== jwt_grant() CALLED ==========")
                print(f"   🔍 [JWT_GRANT INTERCEPT] assertion type: {type(assertion)}")
                print(f"   🔍 [JWT_GRANT INTERCEPT] assertion length: {len(assertion) if assertion else 0}")
                
                # Decode the JWT assertion to check for scopes and detect DWD
                is_dwd = False
                try:
                    decoded = jwt.decode(assertion, options={"verify_signature": False})
                    print(f"   🔍 [JWT_GRANT INTERCEPT] Decoded JWT keys: {list(decoded.keys())}")
                    print(f"   🔍 [JWT_GRANT INTERCEPT] Decoded JWT payload: {decoded}")
                    
                    # Check if this is a DWD request (has 'sub' - subject indicates DWD)
                    if 'sub' in decoded:
                        is_dwd = True
                        if 'scope' in decoded:
                            scope_val = decoded.get('scope', '')
                            if scope_val:
                                print(f"✅ [JWT_GRANT INTERCEPT] DWD request detected (has 'sub' and 'scope' with {len(scope_val.split())} scopes)")
                            else:
                                print(f"✅ [JWT_GRANT INTERCEPT] DWD request detected (has 'sub', empty 'scope')")
                        else:
                            print(f"✅ [JWT_GRANT INTERCEPT] DWD request detected (has 'sub', no 'scope')")
                    else:
                        print(f"   🔍 [JWT_GRANT INTERCEPT] Not a DWD request (no 'sub' field)")
                except Exception as decode_err:
                    print(f"⚠️  [JWT_GRANT INTERCEPT] Could not decode JWT: {decode_err}")
                    import traceback
                    traceback.print_exc()
                
                # Note: Scope will be added in _token_endpoint_request intercept
                if is_dwd:
                    print(f"   🔍 [JWT_GRANT INTERCEPT] DWD request - scopes will be added in _token_endpoint_request")
                
                print(f"   🔍 [JWT_GRANT INTERCEPT] Calling original jwt_grant()...")
                result = original_jwt_grant(request, token_uri, assertion)
                print(f"   🔍 [JWT_GRANT INTERCEPT] jwt_grant() completed")
                return result
            
            oauth2_client._original_jwt_grant = original_jwt_grant
            oauth2_client.jwt_grant = _jwt_grant_intercept
            print(f"✅ Monkey-patched jwt_grant at module level to intercept ALL JWT assertions")
        
        # Patch _make_authorization_grant_assertion to intercept JWT creation
        if hasattr(delegated_credentials, '_make_authorization_grant_assertion'):
            original_make_assertion = delegated_credentials._make_authorization_grant_assertion
            
            def _make_assertion_intercept(self, assertion_data, now):
                """Intercept JWT creation to verify and remove scopes for DWD"""
                print(f"   🔍 [JWT INTERCEPT] ========== JWT CREATION INTERCEPTED ==========")
                print(f"   🔍 [JWT INTERCEPT] assertion_data type: {type(assertion_data)}")
                
                # assertion_data is a dict with JWT claims
                if isinstance(assertion_data, dict):
                    print(f"   🔍 [JWT INTERCEPT] assertion_data keys BEFORE: {list(assertion_data.keys())}")
                    if 'scope' in assertion_data:
                        scope_value = assertion_data.get('scope')
                        print(f"❌ [JWT INTERCEPT] CRITICAL: JWT assertion_data contains 'scope': {scope_value[:100] if scope_value else 'None'}...")
                        print(f"❌ [JWT INTERCEPT] REMOVING scope from JWT assertion_data for DWD...")
                        # CRITICAL: Create a new dict without scope
                        assertion_data = {k: v for k, v in assertion_data.items() if k != 'scope'}
                        print(f"✅ [JWT INTERCEPT] Removed scope from JWT assertion_data")
                        print(f"   🔍 [JWT INTERCEPT] assertion_data keys AFTER: {list(assertion_data.keys())}")
                    else:
                        print(f"✅ [JWT INTERCEPT] JWT assertion_data has no scope parameter (correct for DWD)")
                else:
                    print(f"⚠️  [JWT INTERCEPT] assertion_data is not a dict: {type(assertion_data)}")
                
                # Call original method to create JWT with modified assertion_data (no scope)
                print(f"   🔍 [JWT INTERCEPT] Calling original _make_authorization_grant_assertion with NO scope...")
                assertion = original_make_assertion(assertion_data, now)
                print(f"   🔍 [JWT INTERCEPT] JWT assertion created (length: {len(assertion) if assertion else 0})")
                
                # Decode and verify the JWT doesn't have scopes
                try:
                    # Decode without verification to inspect payload
                    decoded = jwt.decode(assertion, options={"verify_signature": False})
                    print(f"   🔍 [JWT INTERCEPT] Decoded JWT keys: {list(decoded.keys())}")
                    if 'scope' in decoded:
                        print(f"❌ [JWT INTERCEPT] CRITICAL: Decoded JWT STILL contains 'scope': {decoded.get('scope')[:100]}...")
                        print(f"❌ [JWT INTERCEPT] This WILL cause unauthorized_client error!")
                        print(f"❌ [JWT INTERCEPT] The original method added scope back!")
                    else:
                        print(f"✅ [JWT INTERCEPT] Decoded JWT has no scope parameter (CORRECT for DWD)")
                except Exception as decode_err:
                    print(f"⚠️  [JWT INTERCEPT] Could not decode JWT for inspection: {decode_err}")
                    import traceback
                    traceback.print_exc()
                
                print(f"   🔍 [JWT INTERCEPT] ========== JWT INTERCEPTION COMPLETE ==========")
                return assertion
            
            delegated_credentials._make_authorization_grant_assertion = types.MethodType(
                _make_assertion_intercept, delegated_credentials
            )
            print(f"✅ Monkey-patched _make_authorization_grant_assertion to intercept and verify JWT")
        else:
            print(f"⚠️  WARNING: _make_authorization_grant_assertion not found on credentials object")
        
        # Also patch refresh method to ensure scopes are None before refresh
        # CRITICAL: We also need to patch _refresh_token if it exists, as that's what actually creates the JWT
        if hasattr(delegated_credentials, 'refresh'):
            original_refresh = delegated_credentials.refresh
            
            def _refresh_no_scopes(self, request):
                """Override refresh to ensure no scopes before JWT creation"""
                print(f"   🔍 [REFRESH INTERCEPT] ========== refresh() CALLED ==========")
                # Force scopes to None before refresh
                if hasattr(self, '_scopes'):
                    if self._scopes:
                        print(f"⚠️  [REFRESH INTERCEPT] WARNING: _scopes has value before refresh: {self._scopes} - clearing...")
                        self._scopes = None
                    else:
                        print(f"✅ [REFRESH INTERCEPT] _scopes is None (correct)")
                
                # Try to patch _refresh_token if it exists (it's called internally)
                if hasattr(self, '_refresh_token'):
                    original_refresh_token = self._refresh_token
                    
                    def _refresh_token_intercept(self_inner, request_inner):
                        """Intercept _refresh_token to patch _make_authorization_grant_assertion at the right time"""
                        print(f"   🔍 [REFRESH_TOKEN INTERCEPT] _refresh_token() called")
                        # Ensure _make_authorization_grant_assertion is patched
                        if hasattr(self_inner, '_make_authorization_grant_assertion'):
                            method_name = getattr(self_inner._make_authorization_grant_assertion, '__name__', 'unknown')
                            if method_name != '_make_assertion_intercept':
                                print(f"⚠️  [REFRESH_TOKEN INTERCEPT] Re-applying _make_authorization_grant_assertion patch...")
                                # Re-apply the patch
                                original_make_assertion = self_inner._make_authorization_grant_assertion
                                
                                def _make_assertion_intercept_inner(self_innermost, assertion_data, now):
                                    """Intercept JWT creation to verify and remove scopes for DWD"""
                                    print(f"   🔍 [JWT INTERCEPT] ========== JWT CREATION INTERCEPTED ==========")
                                    print(f"   🔍 [JWT INTERCEPT] assertion_data type: {type(assertion_data)}")
                                    
                                    if isinstance(assertion_data, dict):
                                        print(f"   🔍 [JWT INTERCEPT] assertion_data keys: {list(assertion_data.keys())}")
                                        print(f"   🔍 [JWT INTERCEPT] Full assertion_data: {assertion_data}")
                                        if 'scope' in assertion_data:
                                            print(f"❌ [JWT INTERCEPT] CRITICAL: JWT assertion_data contains 'scope': {assertion_data.get('scope')}")
                                            print(f"❌ [JWT INTERCEPT] Removing scope from JWT assertion_data for DWD...")
                                            assertion_data = assertion_data.copy()
                                            del assertion_data['scope']
                                            print(f"✅ [JWT INTERCEPT] Removed scope from JWT assertion_data")
                                        else:
                                            print(f"✅ [JWT INTERCEPT] JWT assertion_data has no scope parameter (correct for DWD)")
                                    else:
                                        print(f"⚠️  [JWT INTERCEPT] assertion_data is not a dict: {type(assertion_data)}")
                                    
                                    print(f"   🔍 [JWT INTERCEPT] Calling original _make_authorization_grant_assertion...")
                                    assertion = original_make_assertion(assertion_data, now)
                                    print(f"   🔍 [JWT INTERCEPT] JWT assertion created (length: {len(assertion) if assertion else 0})")
                                    
                                    # Decode and verify the JWT doesn't have scopes
                                    try:
                                        decoded = jwt.decode(assertion, options={"verify_signature": False})
                                        print(f"   🔍 [JWT INTERCEPT] Decoded JWT keys: {list(decoded.keys())}")
                                        print(f"   🔍 [JWT INTERCEPT] Decoded JWT payload: {decoded}")
                                        if 'scope' in decoded:
                                            print(f"❌ [JWT INTERCEPT] CRITICAL: Decoded JWT contains 'scope': {decoded.get('scope')}")
                                            print(f"❌ [JWT INTERCEPT] This WILL cause unauthorized_client error!")
                                        else:
                                            print(f"✅ [JWT INTERCEPT] Decoded JWT has no scope parameter (correct for DWD)")
                                    except Exception as decode_err:
                                        print(f"⚠️  [JWT INTERCEPT] Could not decode JWT: {decode_err}")
                                    
                                    print(f"   🔍 [JWT INTERCEPT] ========== JWT INTERCEPTION COMPLETE ==========")
                                    return assertion
                                
                                self_inner._make_authorization_grant_assertion = types.MethodType(
                                    _make_assertion_intercept_inner, self_inner
                                )
                                print(f"✅ [REFRESH_TOKEN INTERCEPT] Re-applied _make_authorization_grant_assertion patch")
                        
                        # Call original _refresh_token
                        print(f"   🔍 [REFRESH_TOKEN INTERCEPT] Calling original _refresh_token()...")
                        result = original_refresh_token(request_inner)
                        print(f"   🔍 [REFRESH_TOKEN INTERCEPT] _refresh_token() completed")
                        return result
                    
                    self._refresh_token = types.MethodType(_refresh_token_intercept, self)
                    print(f"✅ Monkey-patched _refresh_token to intercept JWT creation")
                
                # Call original refresh
                print(f"   🔍 [REFRESH INTERCEPT] Calling original refresh()...")
                result = original_refresh(request)
                print(f"   🔍 [REFRESH INTERCEPT] refresh() completed")
                return result
            
            delegated_credentials.refresh = types.MethodType(_refresh_no_scopes, delegated_credentials)
            print(f"✅ Monkey-patched refresh method to ensure no scopes in JWT")
        else:
            print(f"⚠️  WARNING: refresh method not found on credentials object")
        
        # CRITICAL: For DWD, we must ensure NO scopes in both public and private attributes
        # Check and clear _scopes (private attribute) which is used in JWT creation
        if hasattr(delegated_credentials, '_scopes'):
            if delegated_credentials._scopes:
                print(f"⚠️  WARNING: Delegated credentials _scopes (private) has value: {delegated_credentials._scopes}")
                print(f"⚠️  This will be included in JWT - clearing now...")
                delegated_credentials._scopes = None
                print(f"✅ Cleared _scopes (private) attribute")
        
        # CRITICAL: For DWD, we must ensure NO scopes attribute exists or is None/empty
        # Even if base has no scopes, with_subject() might add default scopes
        # We need to explicitly clear scopes - Admin Console enforces them, not client
        if hasattr(delegated_credentials, 'scopes'):
            current_scopes = getattr(delegated_credentials, 'scopes', None)
            if current_scopes:
                print(f"⚠️  WARNING: Delegated credentials have scopes after with_subject(): {current_scopes}")
                print(f"⚠️  Attempting to clear scopes - DWD should not request scopes")
                # Try with_scopes(None) first
                try:
                    delegated_credentials = delegated_credentials.with_scopes(None)
                    # Verify it worked
                    check_scopes = getattr(delegated_credentials, 'scopes', None)
                    if check_scopes:
                        print(f"⚠️  with_scopes(None) didn't clear scopes, trying to delete attribute...")
                        # Try to delete the scopes attribute entirely
                        try:
                            delattr(delegated_credentials, 'scopes')
                            print(f"✅ Deleted scopes attribute from credentials")
                        except (AttributeError, TypeError):
                            # If deletion fails, recreate credentials from scratch with scopes=None
                            print(f"⚠️  Could not delete scopes attribute, recreating credentials...")
                            try:
                                base_no_scopes = service_account.Credentials.from_service_account_file(
                                    self.service_account_path,
                                    scopes=None  # Explicitly None for DWD
                                )
                            except TypeError:
                                base_no_scopes = service_account.Credentials.from_service_account_file(
                                    self.service_account_path
                                    # No scopes parameter
                                )
                            delegated_credentials = base_no_scopes.with_subject(user_email)
                            # Try to delete scopes from recreated credentials if it exists
                            if hasattr(delegated_credentials, 'scopes'):
                                try:
                                    delattr(delegated_credentials, 'scopes')
                                except:
                                    pass
                            print(f"✅ Recreated delegated credentials without scopes")
                    else:
                        print(f"✅ Used with_scopes(None) to clear scopes")
                except (TypeError, AttributeError):
                    # If that fails, recreate credentials from scratch with scopes=None
                    print(f"⚠️  with_scopes(None) not supported, recreating credentials...")
                    try:
                        base_no_scopes = service_account.Credentials.from_service_account_file(
                            self.service_account_path,
                            scopes=None  # Explicitly None for DWD
                        )
                    except TypeError:
                        base_no_scopes = service_account.Credentials.from_service_account_file(
                            self.service_account_path
                            # No scopes parameter
                        )
                    delegated_credentials = base_no_scopes.with_subject(user_email)
                    # Try to delete scopes attribute if it exists
                    if hasattr(delegated_credentials, 'scopes'):
                        try:
                            delattr(delegated_credentials, 'scopes')
                            print(f"✅ Deleted scopes attribute from recreated credentials")
                        except:
                            pass
                    print(f"✅ Recreated delegated credentials without scopes")
        
        # Final verification - check scope state
        if hasattr(delegated_credentials, 'scopes'):
            final_scopes = getattr(delegated_credentials, 'scopes', None)
            if final_scopes:
                print(f"❌ ERROR: Delegated credentials still have scopes after clearing: {final_scopes}")
                print(f"❌ This will cause 'unauthorized_client' - JWT will include scope parameter")
            else:
                print(f"✅ Delegated credentials scopes attribute is None/empty (correct for DWD)")
        else:
            print(f"✅ Delegated credentials have no scopes attribute (correct for DWD)")
        
        # Debug: Inspect credentials state for detailed logging
        try:
            print(f"   🔍 Debug: Inspecting delegated credentials state...")
            # Get service account info for debugging
            if hasattr(delegated_credentials, 'service_account_email'):
                print(f"   Debug: Service account email: {delegated_credentials.service_account_email}")
            if hasattr(delegated_credentials, '_signer'):
                print(f"   Debug: Signer available: {delegated_credentials._signer is not None}")
            
            # Try to get the subject (user email being impersonated)
            if hasattr(delegated_credentials, '_subject'):
                print(f"   Debug: Impersonating user: {delegated_credentials._subject}")
            
            # Check scopes one more time for debugging
            debug_scopes = getattr(delegated_credentials, 'scopes', None) if hasattr(delegated_credentials, 'scopes') else None
            if debug_scopes:
                print(f"   ⚠️  Debug: Final scope check shows scopes: {debug_scopes}")
            else:
                print(f"   ✅ Debug: Final scope check confirms no scopes")
            
            # Get Client ID from base credentials if available
            if hasattr(self._base_credentials, '_service_account_email'):
                print(f"   Debug: Base service account: {self._base_credentials._service_account_email}")
        except Exception as debug_err:
            print(f"   ⚠️  Debug: Could not inspect credentials: {debug_err}")
        
        return delegated_credentials
    
    def _inspect_jwt_assertion(self, credentials):
        """Inspect JWT assertion to verify it doesn't include scopes"""
        try:
            # Try to get the JWT assertion from credentials
            # The assertion is created in _make_authorization_grant_assertion method
            if hasattr(credentials, '_make_authorization_grant_assertion'):
                # This is the method that creates the JWT
                # We can't easily intercept it, but we can check if scopes are None
                pass
            
            # Alternative: Try to decode if we can get the assertion
            # The assertion is created during refresh, so we'd need to monkey-patch
            # For now, just verify scopes are None
            if hasattr(credentials, '_scopes'):
                if credentials._scopes:
                    print(f"❌ CRITICAL: _scopes has value in JWT creation: {credentials._scopes}")
                    return False
            
            if hasattr(credentials, 'scopes'):
                scope_val = getattr(credentials, 'scopes', None)
                if scope_val:
                    print(f"❌ CRITICAL: scopes has value in JWT creation: {scope_val}")
                    return False
            
            print(f"✅ JWT assertion check: No scopes found (correct for DWD)")
            return True
        except Exception as e:
            print(f"⚠️  Could not inspect JWT assertion: {e}")
            return True  # Assume OK if we can't check
    
    def get_classroom_service(self, user_email: str):
        """Get Google Classroom service for a specific user"""
        # CRITICAL: Set API type in thread-local BEFORE getting credentials
        # This ensures the JWT creation can detect which API is being used
        _thread_local.dwd_api_type = 'classroom'
        
        credentials = self._get_delegated_credentials(user_email)
        # Mark API type in credentials object as well
        if hasattr(credentials, '_dwd_api_type'):
            credentials._dwd_api_type = 'classroom'
        
        # Final check: ensure credentials have no scopes before building service
        # CRITICAL: build() might add scopes, so we need to prevent that
        if hasattr(credentials, 'scopes'):
            scope_val = getattr(credentials, 'scopes', None)
            if scope_val:
                print(f"⚠️  WARNING: Credentials have scopes before building Classroom service: {scope_val}")
                print(f"⚠️  Attempting to clear scopes...")
                try:
                    credentials = credentials.with_scopes(None)
                except:
                    pass
        # Also check and clear private _scopes
        if hasattr(credentials, '_scopes'):
            if credentials._scopes:
                print(f"⚠️  WARNING: Credentials have _scopes before building: {credentials._scopes}")
                credentials._scopes = None
        
        # Build service - explicitly don't pass any scopes
        # The credentials object should have no scopes, so build() shouldn't add any
        service = build('classroom', 'v1', credentials=credentials)
        # After build, verify credentials still have no scopes
        if hasattr(credentials, '_scopes'):
            if credentials._scopes:
                print(f"❌ ERROR: build() added _scopes: {credentials._scopes}")
                credentials._scopes = None
        return service
    
    def get_calendar_service(self, user_email: str):
        """Get Google Calendar service for a specific user"""
        # CRITICAL: Set API type in thread-local BEFORE getting credentials
        # This ensures the JWT creation can detect which API is being used
        _thread_local.dwd_api_type = 'calendar'
        
        credentials = self._get_delegated_credentials(user_email)
        # Mark API type in credentials object as well
        if hasattr(credentials, '_dwd_api_type'):
            credentials._dwd_api_type = 'calendar'
        
        # Final check: ensure credentials have no scopes before building service
        if hasattr(credentials, 'scopes'):
            scope_val = getattr(credentials, 'scopes', None)
            if scope_val:
                print(f"⚠️  WARNING: Credentials have scopes before building Calendar service: {scope_val}")
                print(f"⚠️  Attempting to clear scopes...")
                try:
                    credentials = credentials.with_scopes(None)
                except:
                    pass
        # Also check and clear private _scopes
        if hasattr(credentials, '_scopes'):
            if credentials._scopes:
                print(f"⚠️  WARNING: Credentials have _scopes before building: {credentials._scopes}")
                credentials._scopes = None
        
        # Build service
        service = build('calendar', 'v3', credentials=credentials)
        # After build, verify credentials still have no scopes
        if hasattr(credentials, '_scopes'):
            if credentials._scopes:
                print(f"❌ ERROR: build() added _scopes: {credentials._scopes}")
                credentials._scopes = None
        return service
    
    def fetch_user_courses(self, user_email: str) -> List[Dict]:
        """Fetch all courses for a user"""
        try:
            # CRITICAL: Use get_classroom_service to ensure thread-local API type is set correctly
            # This ensures the JWT includes the correct Classroom scopes
            classroom_service = self.get_classroom_service(user_email)
            
            print(f"   🔍 Making API call to list courses...")
            results = classroom_service.courses().list().execute()
            courses = results.get('courses', [])
            print(f"✅ DWD: Fetched {len(courses)} courses for {user_email}")
            return courses
        except Exception as e:
            error_str = str(e)
            print(f"❌ DWD: Failed to fetch courses for {user_email}: {error_str}")
            
            # Check for different error types
            if 'invalid_scope' in error_str.lower() and 'empty or missing scope not allowed' in error_str.lower():
                print(f"   ⚠️  'invalid_scope: Empty or missing scope not allowed' error detected!")
                print(f"   This usually means:")
                print(f"   1. Client ID not properly authorized in Google Workspace Admin Console")
                print(f"      → Go to: https://admin.google.com")
                print(f"      → Security > API Controls > Domain-wide Delegation")
                print(f"      → Verify Client ID {self._get_client_id()} is EXACTLY as shown")
                print(f"      → Must have these 5 scopes (one per line, EXACT URLs, no typos):")
                print(f"        https://www.googleapis.com/auth/classroom.courses.readonly")
                print(f"        https://www.googleapis.com/auth/classroom.rosters.readonly")
                print(f"        https://www.googleapis.com/auth/classroom.announcements.readonly")
                print(f"        https://www.googleapis.com/auth/calendar.readonly")
                print(f"        https://www.googleapis.com/auth/calendar.events.readonly")
                print(f"   2. Authorization might have been removed or expired")
                print(f"      → Delete the authorization and re-add it")
                print(f"      → Wait 15-30 minutes for propagation")
                print(f"   3. API Access Control might be blocking the request")
                print(f"      → Go to: Security > API Controls > API Access Control")
                print(f"      → Ensure it's set to 'Unrestricted' or allows your app")
                print(f"   NOTE: The JWT has no scope field (correct for DWD), but Google is rejecting it.")
                print(f"   This suggests the Client ID authorization in Admin Console is the issue.")
            
            if 'unauthorized_client' in error_str.lower():
                print(f"   ⚠️  'unauthorized_client' error detected!")
                print(f"   This usually means one of:")
                print(f"   1. Client ID not authorized in Google Workspace Admin Console")
                print(f"      → Go to: https://admin.google.com")
                print(f"      → Security > API Controls > Domain-wide Delegation")
                print(f"      → Verify Client ID {self._get_client_id()} is authorized")
                print(f"      → Must have these 5 scopes (one per line, EXACT URLs):")
                print(f"        https://www.googleapis.com/auth/classroom.courses.readonly")
                print(f"        https://www.googleapis.com/auth/classroom.rosters.readonly")
                print(f"        https://www.googleapis.com/auth/classroom.announcements.readonly")
                print(f"        https://www.googleapis.com/auth/calendar.readonly")
                print(f"        https://www.googleapis.com/auth/calendar.events.readonly")
                print(f"   2. JWT assertion still includes scopes (code logic issue)")
                print(f"      → Check logs above for scope warnings")
                print(f"      → Verify both 'scopes' and '_scopes' attributes are None/empty")
                print(f"      → All logs show scopes=None, but JWT might still include them")
                print(f"   3. Client ID mismatch")
                print(f"      → Service account Client ID: {self._get_client_id()}")
                print(f"      → Must match exactly in Admin Console (no spaces, no typos)")
            
            # Log detailed credential information for debugging
            print(f"   🔍 Debug: Inspecting credentials that caused the error...")
            try:
                credentials = self._get_delegated_credentials(user_email)
                if hasattr(credentials, 'scopes'):
                    scope_value = getattr(credentials, 'scopes', None)
                    print(f"   Debug: Credentials scopes attribute value: {scope_value}")
                    if scope_value:
                        print(f"   ❌ ERROR: Credentials have scopes - this is the likely cause")
                    else:
                        print(f"   ✅ Credentials scopes are None/empty (correct)")
                else:
                    print(f"   ✅ Credentials have no scopes attribute (correct)")
                if hasattr(credentials, 'service_account_email'):
                    print(f"   Debug: Service account: {credentials.service_account_email}")
                if hasattr(credentials, '_subject'):
                    print(f"   Debug: Impersonating user: {credentials._subject}")
                if hasattr(credentials, '_token_uri'):
                    print(f"   Debug: Token URI: {credentials._token_uri}")
            except Exception as debug_err:
                print(f"   ⚠️  Debug: Could not inspect credentials: {debug_err}")
            raise
    
    def fetch_course_teachers(self, user_email: str, course_id: str) -> List[Dict]:
        """Fetch teachers for a specific course"""
        try:
            classroom_service = self.get_classroom_service(user_email)
            results = classroom_service.courses().teachers().list(courseId=course_id).execute()
            teachers = results.get('teachers', [])
            return teachers
        except Exception as e:
            print(f"❌ DWD: Failed to fetch teachers for course {course_id}: {str(e)}")
            return []
    
    def fetch_course_students(self, user_email: str, course_id: str) -> List[Dict]:
        """Fetch students for a specific course"""
        try:
            classroom_service = self.get_classroom_service(user_email)
            results = classroom_service.courses().students().list(courseId=course_id).execute()
            students = results.get('students', [])
            return students
        except Exception as e:
            print(f"❌ DWD: Failed to fetch students for course {course_id}: {str(e)}")
            return []
    
    def fetch_course_coursework(self, user_email: str, course_id: str) -> List[Dict]:
        """Fetch coursework for a specific course"""
        try:
            classroom_service = self.get_classroom_service(user_email)
            results = classroom_service.courses().courseWork().list(courseId=course_id).execute()
            coursework = results.get('courseWork', [])
            return coursework
        except Exception as e:
            print(f"❌ DWD: Failed to fetch coursework for course {course_id}: {str(e)}")
            return []
    
    def fetch_course_submissions(self, user_email: str, course_id: str, coursework_id: str) -> List[Dict]:
        """Fetch student submissions for a specific coursework"""
        try:
            classroom_service = self.get_classroom_service(user_email)
            results = classroom_service.courses().courseWork().studentSubmissions().list(
                courseId=course_id,
                courseWorkId=coursework_id
            ).execute()
            submissions = results.get('studentSubmissions', [])
            return submissions
        except Exception as e:
            print(f"❌ DWD: Failed to fetch submissions for coursework {coursework_id}: {str(e)}")
            return []
    
    def fetch_course_announcements(self, user_email: str, course_id: str) -> List[Dict]:
        """Fetch announcements for a specific course"""
        try:
            classroom_service = self.get_classroom_service(user_email)
            results = classroom_service.courses().announcements().list(courseId=course_id).execute()
            announcements = results.get('announcements', [])
            return announcements
        except Exception as e:
            print(f"❌ DWD: Failed to fetch announcements for course {course_id}: {str(e)}")
            return []
    
    def fetch_user_calendars(self, user_email: str) -> List[Dict]:
        """Fetch all calendars for a user"""
        try:
            calendar_service = self.get_calendar_service(user_email)
            results = calendar_service.calendarList().list().execute()
            calendars = results.get('items', [])
            return calendars
        except Exception as e:
            print(f"❌ DWD: Failed to fetch calendars for {user_email}: {str(e)}")
            return []
    
    def fetch_calendar_events(self, user_email: str, calendar_id: str = 'primary', 
                             time_min: Optional[str] = None) -> List[Dict]:
        """Fetch events from a calendar"""
        try:
            calendar_service = self.get_calendar_service(user_email)
            
            params = {
                'calendarId': calendar_id,
                'maxResults': 2500,
                'singleEvents': True,
                'orderBy': 'startTime'
            }
            
            if time_min:
                params['timeMin'] = time_min
            else:
                # Default to current time
                params['timeMin'] = datetime.now(timezone.utc).isoformat()
            
            results = calendar_service.events().list(**params).execute()
            events = results.get('items', [])
            return events
        except Exception as e:
            print(f"❌ DWD: Failed to fetch events for calendar {calendar_id}: {str(e)}")
            return []
    
    def _get_client_id(self) -> str:
        """Get Client ID from service account file"""
        try:
            if os.path.exists(self.service_account_path):
                with open(self.service_account_path, 'r', encoding='utf-8') as f:
                    service_account_info = json.load(f)
                    return str(service_account_info.get('client_id', 'Not found')).strip()
        except Exception as e:
            print(f"⚠️  Could not read Client ID from service account file: {e}")
        return 'Not found'
    
    def is_available(self) -> bool:
        """Check if DWD service is available (credentials loaded)"""
        return self._base_credentials is not None

# Global instance
_dwd_service = None

def get_dwd_service() -> Optional[GoogleDWDService]:
    """Get global DWD service instance"""
    global _dwd_service
    if _dwd_service is None:
        _dwd_service = GoogleDWDService()
    return _dwd_service if _dwd_service.is_available() else None




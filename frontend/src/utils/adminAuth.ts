// Admin authentication utilities
// Default admin emails - any user with admin_privileges=true can be admin
export const ADMIN_EMAILS = [
  'services@atsnai.com',
  'dhruvilv2001@gmail.com',
  'dhruvilvaghela2003@gmail.com',
  'dummy@learners.prakriti.org.in'
]; // Available admin emails
export const ADMIN_PASSWORD = 'admin123'; // Not used with Supabase auth

export const adminLogin = async (email: string, password: string) => {
  try {
    const response = await fetch('/api/admin/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    });

    if (response.ok) {
      const data = await response.json();
      localStorage.setItem('admin_token', data.access_token);
      return { success: true, data };
    } else {
      const errorData = await response.json();
      return { success: false, error: errorData.detail || 'Login failed' };
    }
  } catch {
    return { success: false, error: 'Network error' };
  }
};

export const adminLogout = () => {
  localStorage.removeItem('admin_token');
};

export const getAdminToken = () => {
  return localStorage.getItem('admin_token');
};

export const isAdminAuthenticated = () => {
  return !!localStorage.getItem('admin_token');
};


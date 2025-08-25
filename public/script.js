// Global app script for NoteManager
(function () {
  // Helper: get element safely
  const $ = (sel) => document.querySelector(sel);

  /**
   * Apply the preferred color theme to the document root.
   *
   * Determines the effective theme by reading a persisted preference from localStorage ('dark' or 'light')
   * and falling back to the OS-level preference (prefers-color-scheme). It then ensures `document.documentElement`
   * has the `dark` class when dark mode is chosen and the `light` class when light mode is chosen.
   *
   * This function has no return value and may fail silently (e.g., in environments where access to
   * window.matchMedia or localStorage is restricted).
   */
  function applyPreferredTheme() {
    try {
      const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
      const saved = localStorage.getItem('theme'); // 'dark' | 'light' | null
      const isDark = saved ? saved === 'dark' : prefersDark;
      document.documentElement.classList.toggle('dark', isDark);
      document.documentElement.classList.toggle('light', !isDark);
    } catch (e) { }
  }
  applyPreferredTheme();

  const themeBtn = $('#toggleTheme');
  if (themeBtn) {
    themeBtn.addEventListener('click', () => {
      const isDark = !document.documentElement.classList.contains('dark');
      document.documentElement.classList.toggle('dark', isDark);
      document.documentElement.classList.toggle('light', !isDark);
      try { localStorage.setItem('theme', isDark ? 'dark' : 'light'); } catch (e) { }
    });
  }

  // LOGIN: handle submit on index.html
  const loginForm = $('#loginForm');
  if (loginForm) {
    const usernameEl = $('#username');
    const passwordEl = $('#password');
    const submitBtn = $('#submitBtn');
    const errorBox = $('#errorBox');

    const setLoading = (isLoading) => {
      if (!submitBtn) return;
      submitBtn.disabled = isLoading;
      submitBtn.classList.toggle('opacity-60', isLoading);
      submitBtn.classList.toggle('cursor-not-allowed', isLoading);
      submitBtn.innerText = isLoading ? 'Wird geprüft…' : 'Login';
    };

    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const username = usernameEl?.value.trim();
      const passwd = passwordEl?.value;

      if (!username || !passwd) {
        if (errorBox) {
          errorBox.textContent = 'Bitte Benutzername und Passwort eingeben.';
          errorBox.classList.remove('hidden');
        }
        return;
      }

      setLoading(true);
      try {
        const url = `/user/verify?username=${encodeURIComponent(username)}&passwd=${encodeURIComponent(passwd)}`;
        const res = await fetch(url, { method: 'GET' });
        const data = await res.json();
        if (data?.success) {
          // small delay for UX
          window.location.href = '/home';
        } else {
          if (errorBox) {
            errorBox.textContent = data?.error || 'Ungültige Anmeldedaten.';
            errorBox.classList.remove('hidden');
          }
        }
      } catch (err) {
        console.error(err)
        if (errorBox) {
          errorBox.textContent = 'Serverfehler. Bitte später erneut versuchen.';
          errorBox.classList.remove('hidden');
        }
      } finally {
        setLoading(false);
      }
    });
  }

  // HOME: Sidebar toggle
  const sidebar = $('#sidebar');
  const toggleSidebarBtn = $('#toggleSidebar');
  if (sidebar && toggleSidebarBtn) {
    let collapsed = false;
    toggleSidebarBtn.addEventListener('click', () => {
      collapsed = !collapsed;
      if (collapsed) {
        sidebar.classList.add('w-16', 'p-2');
        sidebar.classList.remove('w-64', 'p-4');
        toggleSidebarBtn.textContent = '✕'; // Close icon
      } else {
        sidebar.classList.add('w-64', 'p-4');
        sidebar.classList.remove('w-16', 'p-2');
        toggleSidebarBtn.textContent = '☰'; // Burger icon
      }
    });
  }
})

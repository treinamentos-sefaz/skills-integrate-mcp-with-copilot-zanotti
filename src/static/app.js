document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const signupContainer = document.getElementById("signup-container");
  const messageDiv = document.getElementById("message");
  const accountButton = document.getElementById("account-button");
  const accountMenu = document.getElementById("account-menu");
  const showLogin = document.getElementById("show-login");
  const logoutButton = document.getElementById("logout");
  const loginDialog = document.getElementById("login-dialog");
  const loginForm = document.getElementById("login-form");
  const loginError = document.getElementById("login-error");
  let authenticated = false;

  function showMessage(message, type) {
    messageDiv.textContent = message;
    messageDiv.className = type;
  }

  function updateAuthUI() {
    signupContainer.classList.toggle("hidden", !authenticated);
    showLogin.classList.toggle("hidden", authenticated);
    logoutButton.classList.toggle("hidden", !authenticated);
  }

  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      if (!response.ok) throw new Error("Could not load activities");
      const activities = await response.json();
      activitiesList.replaceChildren();
      activitySelect.replaceChildren(new Option("-- Select an activity --", ""));

      Object.entries(activities).forEach(([name, details]) => {
        const card = document.createElement("div");
        card.className = "activity-card";
        const title = document.createElement("h4");
        title.textContent = name;
        const description = document.createElement("p");
        description.textContent = details.description;
        const schedule = document.createElement("p");
        schedule.textContent = `Schedule: ${details.schedule}`;
        const availability = document.createElement("p");
        availability.textContent = `Availability: ${details.max_participants - details.participants.length} spots left`;
        card.append(title, description, schedule, availability);

        const participants = document.createElement("div");
        participants.className = "participants-container";
        if (details.participants.length) {
          const section = document.createElement("div");
          section.className = "participants-section";
          const heading = document.createElement("h5");
          heading.textContent = "Participants:";
          const list = document.createElement("ul");
          list.className = "participants-list";
          details.participants.forEach((email) => {
            const item = document.createElement("li");
            const label = document.createElement("span");
            label.className = "participant-email";
            label.textContent = email;
            item.appendChild(label);
            if (authenticated) {
              const button = document.createElement("button");
              button.className = "delete-btn";
              button.type = "button";
              button.textContent = "❌";
              button.setAttribute("aria-label", `Unregister ${email}`);
              button.addEventListener("click", () => unregister(name, email));
              item.appendChild(button);
            }
            list.appendChild(item);
          });
          section.append(heading, list);
          participants.appendChild(section);
        } else {
          participants.textContent = "No participants yet";
        }
        card.appendChild(participants);
        activitiesList.appendChild(card);
        activitySelect.add(new Option(name, name));
      });
    } catch (error) {
      activitiesList.textContent = "Failed to load activities. Please try again later.";
      console.error("Error fetching activities:", error);
    }
  }

  async function updateRegistration(url, method) {
    try {
      const response = await fetch(url, {
        method,
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      const result = await response.json();
      if (response.ok) {
        showMessage(result.message, "success");
        signupForm.reset();
        await fetchActivities();
      } else {
        showMessage(result.detail || "An error occurred", "error");
        if (response.status === 401) {
          authenticated = false;
          updateAuthUI();
          await fetchActivities();
        }
      }
    } catch (error) {
      showMessage("Request failed. Please try again.", "error");
      console.error("Registration request failed:", error);
    }
  }

  function unregister(activity, email) {
    return updateRegistration(
      `/activities/${encodeURIComponent(activity)}/unregister?email=${encodeURIComponent(email)}`,
      "DELETE"
    );
  }

  signupForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const email = document.getElementById("email").value;
    const activity = activitySelect.value;
    updateRegistration(
      `/activities/${encodeURIComponent(activity)}/signup?email=${encodeURIComponent(email)}`,
      "POST"
    );
  });

  accountButton.addEventListener("click", () => {
    const open = accountMenu.classList.toggle("hidden") === false;
    accountButton.setAttribute("aria-expanded", String(open));
  });
  showLogin.addEventListener("click", () => {
    accountMenu.classList.add("hidden");
    accountButton.setAttribute("aria-expanded", "false");
    loginError.classList.add("hidden");
    loginDialog.showModal();
  });
  document.getElementById("cancel-login").addEventListener("click", () => {
    loginForm.reset();
    loginDialog.close();
  });
  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: document.getElementById("username").value,
          password: document.getElementById("password").value,
        }),
      });
      const result = await response.json();
      if (!response.ok) {
        loginError.textContent = result.detail || "Login failed";
        loginError.classList.remove("hidden");
        return;
      }
      authenticated = true;
      loginForm.reset();
      loginDialog.close();
      updateAuthUI();
      await fetchActivities();
    } catch (error) {
      loginError.textContent = "Login failed. Please try again.";
      loginError.classList.remove("hidden");
      console.error("Login failed:", error);
    }
  });
  logoutButton.addEventListener("click", async () => {
    try {
      const response = await fetch("/auth/logout", {
        method: "POST",
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      if (!response.ok && response.status !== 401) throw new Error("Logout failed");
      authenticated = false;
      accountMenu.classList.add("hidden");
      accountButton.setAttribute("aria-expanded", "false");
      updateAuthUI();
      await fetchActivities();
    } catch (error) {
      showMessage("Logout failed. Please try again.", "error");
      console.error("Logout failed:", error);
    }
  });

  async function initialize() {
    try {
      const response = await fetch("/auth/session");
      if (!response.ok) throw new Error("Could not check session");
      const session = await response.json();
      authenticated = session.authenticated;
    } catch (error) {
      showMessage("Could not check teacher login status.", "error");
      console.error("Session check failed:", error);
    }
    updateAuthUI();
    await fetchActivities();
  }
  initialize();
});
